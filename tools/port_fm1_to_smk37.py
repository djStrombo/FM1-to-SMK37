#!/usr/bin/env python3
"""
Automated Porting Tool: FM-1 (Felucca / SLOOP Family) -> M-VAVE SMK-37 Pro & Elite
Injects the SMK-37 hardware HAL, ST7789 SPI Group A display driver, WS2812 pad LEDs,
37-key velocity matrix, encoder/fader inputs, flash protection, and GitHub Actions build workflow.
"""

import os
import sys
import shutil
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
MELODEE_DIR = BASE_DIR.parent / "Firmwares Ports" / "melodee-smk37"
if not MELODEE_DIR.exists():
    MELODEE_DIR = BASE_DIR / "melodee-smk37"

def port_repo_to_smk37(target_repo_dir: Path):
    target_repo_dir = Path(target_repo_dir).resolve()
    print(f"[*] Analyzing target repository: {target_repo_dir}")

    hal_dir = target_repo_dir / "firmware" / "hal"
    src_dir = target_repo_dir / "firmware" / "src"
    tools_dir = target_repo_dir / "tools"

    if not hal_dir.exists() or not (hal_dir / "fm1_lcd_hw.h").exists():
        raise RuntimeError(
            f"Directory '{target_repo_dir}' does not appear to be a Felucca/FM-1 HAL repository. "
            "Missing firmware/hal/fm1_lcd_hw.h."
        )

    # 1. Inject smk_input.h, smk_mapping.h, fm1_flash_map.h, smk_midi.h
    print("[*] 1/10 Injecting SMK-37 HAL headers...")
    for hname in ["smk_input.h", "smk_mapping.h", "fm1_flash_map.h", "smk_midi.h"]:
        src_file = MELODEE_DIR / "firmware" / "hal" / hname
        if not src_file.exists():
            src_file = BASE_DIR / hname
        if src_file.exists():
            shutil.copy2(src_file, hal_dir / hname)
            print(f"    -> Copied {hname} to {hal_dir}")

    # 2. Update fm1_lcd_hw.h with BOARD_SMK37 (SPI Group A + Pad LEDs)
    print("[*] 2/8 Patching fm1_lcd_hw.h for SPI1 Group A...")
    lcd_hw_src = (MELODEE_DIR / "firmware" / "hal" / "fm1_lcd_hw.h").read_text(encoding="utf-8")
    (hal_dir / "fm1_lcd_hw.h").write_text(lcd_hw_src, encoding="utf-8")

    # 3. Update firmware/src/lcd.c
    lcd_c_path = src_dir / "lcd.c"
    if lcd_c_path.exists():
        print("[*] 3/8 Patching firmware/src/lcd.c for ST7789 IPS LCD & WS2812 pads...")
        melodee_lcd_c = (MELODEE_DIR / "firmware" / "src" / "lcd.c").read_text(encoding="utf-8")
        lcd_c_path.write_text(melodee_lcd_c, encoding="utf-8")

    # 4. Patch main unit file (felucca.c, choralroot.c, etc.)
    print("[*] 4/8 Wiring smk_input.h into engine source...")
    for c_file in src_dir.glob("*.c"):
        txt = c_file.read_text(encoding="utf-8")
        if '#include "fm1_input.h"' in txt and '#include "smk_input.h"' not in txt:
            print(f"    -> Adding smk_input.h hook to {c_file.name}")
            replacement = (
                "#if BOARD_SMK37\n"
                '#include "smk_input.h"\n'
                "#else\n"
                '#include "fm1_input.h"\n'
                '#include "fm1_adc.h"\n'
                "#endif"
            )
            txt = re.sub(r'#include\s+"fm1_input\.h"(?:\s*#include\s+"fm1_adc\.h")?', replacement, txt)
            c_file.write_text(txt, encoding="utf-8")

    # 5. Patch panel.c for dynamic encoder routing and calibration protection
    panel_c = src_dir / "panel.c"
    if panel_c.exists():
        print("[*] 5/8 Patching firmware/src/panel.c for dynamic SMK-37 encoder & button mapping...")
        ptxt = panel_c.read_text(encoding="utf-8")
        if "#if BOARD_SMK37" not in ptxt:
            # Patch PANEL_DEFAULT
            ptxt = re.sub(
                r'(\{0,\s*1,\s*6,\s*2,\s*3,\s*4,\s*5\},?\s*/\*[^\n]*\*/)',
                '#if BOARD_SMK37\n    {4, 6, 5, 0, 1, 2, 3},                           /* SELECT = enc 4 (K5), ALGO = enc 6 (K7), PRESET = enc 5 (K6), K1..K4 = enc 0..3 */\n#else\n    \\1\n#endif',
                ptxt
            )
            # Patch panel_init
            ptxt = re.sub(
                r'static void panel_init\(void\)[^{]*\{',
                'static void panel_init(void)\n{\n#if BOARD_SMK37\n    panel = PANEL_DEFAULT;\n#else',
                ptxt
            )
            if "#endif\n}" not in ptxt:
                ptxt = re.sub(r'(panel\s*=\s*PANEL_DEFAULT;\s*)\}', r'\1#endif\n}', ptxt)
            # Patch panel_enc
            panel_enc_dyn = (
                "static int32_t panel_enc(uint32_t role)\n"
                "{\n"
                "#if BOARD_SMK37\n"
                "    uint8_t target_act = 0xFF;\n"
                "    switch (role) {\n"
                "        case EN_SELECT: target_act = ENC_ACT_PADSEL; break;\n"
                "        case EN_ALGO:   target_act = ENC_ACT_TEMPO;  break;\n"
                "        case EN_PRESET: target_act = ENC_ACT_SAMPLE; break;\n"
                "        case EN_K1:     target_act = ENC_ACT_KNOB1;  break;\n"
                "        case EN_K2:     target_act = ENC_ACT_KNOB2;  break;\n"
                "        case EN_K3:     target_act = ENC_ACT_KNOB3;  break;\n"
                "        case EN_K4:     target_act = ENC_ACT_KNOB4;  break;\n"
                "        default: break;\n"
                "    }\n"
                "    if (target_act != 0xFF) {\n"
                "        for (uint32_t i = 0; i < 8; i++) {\n"
                "            if (SMK_ENC_MAP[i] == target_act)\n"
                "                return fm1_enc_take(i);\n"
                "        }\n"
                "    }\n"
                "    static const uint8_t def_enc[7] = {4, 6, 5, 0, 1, 2, 3};\n"
                "    if (role < 7)\n"
                "        return fm1_enc_take(def_enc[role]);\n"
                "    return 0;\n"
                "#else\n"
                "    return fm1_enc_take(panel.enc[role]) * panel.dir[role];\n"
                "#endif\n"
                "}"
            )
            ptxt = re.sub(r'static int32_t panel_enc\(uint32_t role\)\s*\{[^}]*\}', panel_enc_dyn, ptxt)
            panel_c.write_text(ptxt, encoding="utf-8")

    # 6. Patch master.c for K8 (ENC_ACT_MASTER) polling
    master_c = src_dir / "master.c"
    if master_c.exists():
        print("[*] 6/8 Patching firmware/src/master.c for SMK-37 master volume knob...")
        mtxt = master_c.read_text(encoding="utf-8")
        if "#if BOARD_SMK37" not in mtxt:
            hook = (
                "static void master_poll(void)\n"
                "{\n"
                "#if BOARD_SMK37\n"
                "    int32_t m_steps = 0;\n"
                "    for (uint32_t k = 0; k < 8; k++) {\n"
                "        if (SMK_ENC_MAP[k] == ENC_ACT_MASTER) {\n"
                "            m_steps = fm1_enc_take(k);\n"
                "            break;\n"
                "        }\n"
                "    }\n"
                "    if (m_steps) {\n"
                "        smk_master = clamp(smk_master + m_steps * 16, 0, 1023);\n"
                "    }\n"
                "#endif\n"
            )
            mtxt = re.sub(r'static void master_poll\(void\)\s*\{', hook, mtxt)
            master_c.write_text(mtxt, encoding="utf-8")

    # 7. Patch UI input loop for physical faders & octave buttons
    cr_ui_c = src_dir / "cr_ui.c"
    ui_in_c = src_dir / "ui_input.c"
    target_ui = cr_ui_c if cr_ui_c.exists() else (ui_in_c if ui_in_c.exists() else None)
    if target_ui:
        print(f"[*] 7/8 Patching {target_ui.name} for faders, octave shifts, and SMK-37 LEDs...")
        utxt = target_ui.read_text(encoding="utf-8")
        if "#if BOARD_SMK37" not in utxt:
            if target_ui == cr_ui_c:
                hook_ui = (
                    "    if (cc.on) {\n"
                    "        cu_calib_input(pe, bm);\n"
                    "        (void)ne;\n"
                    "        return;\n"
                    "    }\n"
                    "#if BOARD_SMK37\n"
                    "    {\n"
                    "        static uint8_t last_fader[4] = {0xFF, 0xFF, 0xFF, 0xFF};\n"
                    "        for (uint32_t f = 0; f < 4u; f++) {\n"
                    "            uint8_t cur_f = fm1_in.fader[f];\n"
                    "            if (last_fader[f] == 0xFF) { last_fader[f] = cur_f; continue; }\n"
                    "            if (cur_f != last_fader[f]) {\n"
                    "                last_fader[f] = cur_f;\n"
                    "                uint8_t fact = (f < 4) ? SMK_FAD_MAP[f] : FAD_ACT_DEFAULT;\n"
                    "                if (fact == FAD_ACT_DEFAULT) fact = (f == 0 ? FAD_ACT_CH1 : f == 1 ? FAD_ACT_CH2 : f == 2 ? FAD_ACT_CH3 : FAD_ACT_CH4);\n"
                    "                switch (fact) {\n"
                    "                    case FAD_ACT_CH1: trk[CR_PART_CHORD].p[P_LEVEL] = (int16_t)cur_f; cu_popup_num(cur_f, 0, \"\", \"chord level\", CR_COL_ORANGE, 0, 127, 12); break;\n"
                    "                    case FAD_ACT_CH2: trk[CR_PART_BASS].p[P_LEVEL] = (int16_t)cur_f; cu_popup_num(cur_f, 0, \"\", \"bass level\", CR_COL_ORANGE, 0, 127, 12); break;\n"
                    "                    case FAD_ACT_CH3: cu_send_set(0, 2, cur_f); cu_popup_num(cur_f, 0, \"\", \"reverb send\", CR_COL_GREEN, 0, 127, 12); break;\n"
                    "                    case FAD_ACT_CH4: case FAD_ACT_MASTER: smk_master = (int32_t)cur_f * 8; break;\n"
                    "                    case FAD_ACT_CUTOFF: trk[CR_PART_CHORD].p[P_ED_FLT] = (int16_t)cur_f; break;\n"
                    "                    case FAD_ACT_RESO: trk[CR_PART_CHORD].p[P_E1] = (int16_t)cur_f; break;\n"
                    "                    default: if (fact >= FAD_ACT_CH1 && fact <= FAD_ACT_CH8) { uint32_t idx = fact - FAD_ACT_CH1; if (idx < NPART) trk[idx].p[P_LEVEL] = (int16_t)cur_f; } break;\n"
                    "                }\n"
                    "            }\n"
                    "        }\n"
                    "        if (pe & (1u << ACT_KBD_OCTDN)) { if (cu.octave > -2) { cu.octave--; song.octave = cu.octave; cu_popup_num(cu.octave, 1, \"\", \"octave\", CR_COL_WHITE, -2, 2, 5); } }\n"
                    "        if (pe & (1u << ACT_KBD_OCTUP)) { if (cu.octave < 2) { cu.octave++; song.octave = cu.octave; cu_popup_num(cu.octave, 1, \"\", \"octave\", CR_COL_WHITE, -2, 2, 5); } }\n"
                    "        if (pe & (1u << ACT_CHORD)) { cu_btn_press(B_EDIT); cu_btn_release(B_EDIT); }\n"
                    "        if (pe & (1u << ACT_REPEAT)) { cu_btn_press(B_ARP); cu_btn_release(B_ARP); }\n"
                    "        if (pe & (1u << ACT_SEL)) { cu_btn_press(B_SCL); cu_btn_release(B_SCL); }\n"
                    "        pe &= ~((1u << ACT_KBD_OCTDN) | (1u << ACT_KBD_OCTUP) | (1u << ACT_CHORD) | (1u << ACT_REPEAT) | (1u << ACT_SEL));\n"
                    "        smk_led_physical(4, cu.octave < 0);\n"
                    "        smk_led_physical(5, cu.octave > 0);\n"
                    "        smk_led_physical(6, cs.perform_on != 0);\n"
                    "        smk_led_physical(16, song.playing != 0);\n"
                    "        smk_led_physical(17, song.rec != 0);\n"
                    "    }\n"
                    "#endif\n"
                )
                utxt = re.sub(r'if\s*\(cc\.on\)\s*\{\s*cu_calib_input\([^;]+;\s*\(void\)ne;\s*return;\s*\}', hook_ui, utxt)
                target_ui.write_text(utxt, encoding="utf-8")
            else:
                # Standard ui_input.c for Felucca / Sloop
                hook_ui = (
                    "#if BOARD_SMK37\n"
                    "    {\n"
                    "        static uint8_t last_fader[4] = {0xFF, 0xFF, 0xFF, 0xFF};\n"
                    "        for (uint32_t f = 0; f < 4u; f++) {\n"
                    "            uint8_t cur_f = fm1_in.fader[f];\n"
                    "            if (last_fader[f] == 0xFF) { last_fader[f] = cur_f; continue; }\n"
                    "            if (cur_f != last_fader[f]) {\n"
                    "                last_fader[f] = cur_f;\n"
                    "                uint8_t fact = (f < 4) ? SMK_FAD_MAP[f] : FAD_ACT_DEFAULT;\n"
                    "                if (fact == FAD_ACT_DEFAULT || fact == FAD_ACT_CH1 + f) {\n"
                    "                    if (f < 4) trk[f].p[P_LEVEL] = (int16_t)cur_f;\n"
                    "                } else if (fact == FAD_ACT_MASTER) {\n"
                    "                    smk_master = (int32_t)cur_f * 8;\n"
                    "                }\n"
                    "                ui.force = 1;\n"
                    "            }\n"
                    "        }\n"
                    "        int32_t m_steps = fm1_enc_take(7);\n"
                    "        if (m_steps) { smk_master = clamp(smk_master + m_steps * 16, 0, 1023); ui.force = 1; }\n"
                    "        if (pressed & (1u << ACT_KBD_OCTDN)) { if (song.octave > -3) { song.octave--; ui.force = 1; } }\n"
                    "        if (pressed & (1u << ACT_KBD_OCTUP)) { if (song.octave < 3) { song.octave++; ui.force = 1; } }\n"
                    "        pressed &= ~((1u << ACT_KBD_OCTDN) | (1u << ACT_KBD_OCTUP));\n"
                    "        smk_led_physical(4, song.octave < 0);\n"
                    "        smk_led_physical(5, song.octave > 0);\n"
                    "        smk_led_physical(16, song.playing != 0);\n"
                    "        smk_led_physical(17, song.rec != 0);\n"
                    "    }\n"
                    "#endif\n"
                )
                utxt = re.sub(r'static void ui_input\(void\)\s*\{\s*uint32_t pressed = fm1_input_edges\(0\)[^;]*;', r'\g<0>\n' + hook_ui, utxt)
                target_ui.write_text(utxt, encoding="utf-8")

    # 8. Patch firmware/src/seq.c for Master MIDI Clock (24 PPQN), Start/Stop, Multitrack & Note Output
    seq_c = src_dir / "seq.c"
    if seq_c.exists():
        print("[*] 8/10 Patching firmware/src/seq.c for Master MIDI Clock & Multitrack routing...")
        seq_code = seq_c.read_text(encoding="utf-8")

        # Top-level includes & clock rules
        if "smk_clk_accum" not in seq_code:
            clock_rule = (
                "/* G_SYNC: 0=INT (no clock), 1=USB (in & out via USB), 2=TRS (out via TRS only) */\n"
                "#define SMK_USB_SEND_CLOCK (song.g[G_SYNC] == 1)\n"
                "#define SMK_TRS_SEND_CLOCK (song.g[G_SYNC] == 2)"
                if "G_SYNC" in seq_code
                else (
                    "#define SMK_USB_SEND_CLOCK (!song.g[G_CLOCK])\n#define SMK_TRS_SEND_CLOCK (song.g[G_CLOCK] != 0)"
                    if "G_CLOCK" in seq_code
                    else "#define SMK_USB_SEND_CLOCK 1\n#define SMK_TRS_SEND_CLOCK 1"
                )
            )
            clock_decl = (
                '#if BOARD_SMK37\n'
                '#include "smk_midi.h"\n'
                'static uint32_t smk_clk_accum __attribute__((section(".bss")));\n'
                f'{clock_rule}\n'
                '#endif\n'
            )
            if "midi_out_note" not in seq_code:
                seq_code = '#define midi_out_note(mc, n, v) do { if (v) midi_out_event(0x09u | ((0x90u | (mc)) << 8) | ((uint32_t)(n) << 16) | ((uint32_t)(v) << 24)); else midi_out_event(0x08u | ((0x80u | (mc)) << 8) | ((uint32_t)(n) << 16)); } while(0)\n' + clock_decl + seq_code
            else:
                seq_code = clock_decl + seq_code

        # Multitrack output routing: ONLY inject if not already handling per-track channels (like G_CH1 in Orbit)
        if "G_CH1" not in seq_code and "static uint32_t trk_midi_ch" in seq_code and "settings_drumch" not in seq_code.split("trk_midi_ch")[1][:250]:
            drum_def = 'static int drum_track(const track_t *t) { return ENGINES[eng_idx(t->eng_req)] == &ENG_DRUM; }\n' if "drum_track" not in seq_code else ''
            seq_code = re.sub(
                r'static\s+uint32_t\s+trk_midi_ch\s*\([^)]*\)\s*\{[^}]*\}',
                drum_def + '''static uint32_t trk_midi_ch(uint32_t i)
{
#if BOARD_SMK37
    if (i < NTRK) {
        if (drum_track(&trk[i]) || i == 3u) return settings_drumch ? (settings_drumch - 1u) : 9u;
        return i % 16u;
    }
    return 0;
#else
    return i % NTRK;
#endif
}''',
                seq_code
            )

        # Adapt mclk_on in seq.c: only USB can slave SMK-37 (TRS is output only)
        orig_mclk = "return song.g[G_SYNC] && mclk.alive && fm1_ms - mclk.last_ms < 500u;"
        if orig_mclk in seq_code and "BOARD_SMK37" not in seq_code.split(orig_mclk)[0][-100:]:
            mclk_rep = (
                "#if BOARD_SMK37\n"
                "    return song.g[G_SYNC] == 1 && mclk.alive && fm1_ms - mclk.last_ms < 500u;\n"
                "#else\n"
                "    return song.g[G_SYNC] && mclk.alive && fm1_ms - mclk.last_ms < 500u;\n"
                "#endif"
            )
            seq_code = seq_code.replace(orig_mclk, mclk_rep, 1)

        # MIDI Transport Start (0xFA) on seq_reset_tracks / song.playing = 1
        if "smk_clk_accum = 0;" not in seq_code:
            orig_start_orbit = "song.playing = 1;\n    slicer_start(pos);"
            orig_start_felucca = "song.playing = 1;\n    slicer_start();"
            if orig_start_orbit in seq_code:
                start_rep = (
                    "song.playing = 1;\n"
                    "#if BOARD_SMK37\n"
                    "    smk_clk_accum = 0;\n"
                    "    if (SMK_TRS_SEND_CLOCK) smk_trs_tx_byte(0xFAu);\n"
                    "    if (SMK_USB_SEND_CLOCK) midi_out_event(0x0Fu | (0xFAu << 8));\n"
                    "#endif\n"
                    "    slicer_start(pos);"
                )
                seq_code = seq_code.replace(orig_start_orbit, start_rep, 1)
            elif orig_start_felucca in seq_code:
                start_rep = (
                    "song.playing = 1;\n"
                    "#if BOARD_SMK37\n"
                    "    smk_clk_accum = 0;\n"
                    "    if (SMK_TRS_SEND_CLOCK) smk_trs_tx_byte(0xFAu);\n"
                    "    if (SMK_USB_SEND_CLOCK) midi_out_event(0x0Fu | (0xFAu << 8));\n"
                    "#endif\n"
                    "    slicer_start();"
                )
                seq_code = seq_code.replace(orig_start_felucca, start_rep, 1)

        # MIDI Transport Stop (0xFC) + All Notes Off in seq_stop
        orig_stop_orbit = "fill_bar_on = 0;\n    song.playing = 0;"
        if orig_stop_orbit in seq_code and "0xFCu" not in seq_code.split("seq_stop")[1][:300]:
            stop_rep = (
                "fill_bar_on = 0;\n"
                "    song.playing = 0;\n"
                "#if BOARD_SMK37\n"
                "    smk_clk_accum = 0;\n"
                "    if (SMK_TRS_SEND_CLOCK) smk_trs_tx_byte(0xFCu);\n"
                "    if (SMK_USB_SEND_CLOCK) midi_out_event(0x0Fu | (0xFCu << 8));\n"
                "    for (uint32_t tr = 0; tr < NTRK; tr++) {\n"
                "        uint32_t mc = trk_midi_ch(tr);\n"
                "        if (mc <= 15u) midi_out_event(0x0Bu | ((0xB0u | mc) << 8) | (123u << 16));\n"
                "    }\n"
                "#endif"
            )
            seq_code = seq_code.replace(orig_stop_orbit, stop_rep, 1)
        elif "seq_stop(void)" in seq_code and "0xFCu" not in seq_code.split("seq_stop")[1][:300]:
            seq_code = re.sub(
                r'(static\s+void\s+seq_stop\s*\([^)]*\)[^{]*\{[^}]*?)(song\.playing\s*=\s*0\s*;)',
                r'\1\2\n#if BOARD_SMK37\n    smk_clk_accum = 0;\n    if (SMK_TRS_SEND_CLOCK) smk_trs_tx_byte(0xFCu);\n    if (SMK_USB_SEND_CLOCK) midi_out_event(0x0Fu | (0xFCu << 8));\n    for (uint32_t tr = 0; tr < NTRK; tr++) {\n        uint32_t mc = trk_midi_ch(tr);\n        if (mc <= 15u) midi_out_event(0x0Bu | ((0xB0u | mc) << 8) | (123u << 16));\n    }\n#endif',
                seq_code,
                count=1
            )

        # MIDI Clock 24 PPQN generation (Orbit events_block or Felucca)
        if "while (clk_pos >= BEAT_U)" in seq_code and "smk_clk_accum += adv;" not in seq_code:
            clk_orbit = '''clk_pos += adv;
#if BOARD_SMK37
        if (SMK_TRS_SEND_CLOCK || (SMK_USB_SEND_CLOCK && !mclk_on())) {
            uint32_t pulse_u = BEAT_U / 24u;
            if (!pulse_u) pulse_u = 1;
            smk_clk_accum += adv;
            if (smk_clk_accum >= pulse_u * 4u) smk_clk_accum = pulse_u;
            while (smk_clk_accum >= pulse_u) {
                smk_clk_accum -= pulse_u;
                if (SMK_TRS_SEND_CLOCK) smk_trs_tx_byte(0xF8u);
                if (SMK_USB_SEND_CLOCK) midi_out_event(0x0Fu | (0xF8u << 8));
            }
        }
#endif'''
            seq_code = seq_code.replace("clk_pos += adv;", clk_orbit, 1)
        elif "click_tick(seq_n);" in seq_code and "smk_clk_accum" not in seq_code.split("click_tick")[1][:400]:
            clk_felucca = '''click_tick(seq_n);
#if BOARD_SMK37
        if (SMK_TRS_SEND_CLOCK || SMK_USB_SEND_CLOCK) {
            uint32_t b_samples = beat_samples();
            if (b_samples) {
                uint32_t pulse_s = b_samples / 24u;
                if (!pulse_s) pulse_s = 1;
                smk_clk_accum += (clock_mode ? seq_n : n);
                while (smk_clk_accum >= pulse_s) {
                    smk_clk_accum -= pulse_s;
                    if (SMK_TRS_SEND_CLOCK) smk_trs_tx_byte(0xF8u);
                    if (SMK_USB_SEND_CLOCK) midi_out_event(0x0Fu | (0xF8u << 8));
                }
            }
        }
#endif'''
            seq_code = seq_code.replace("click_tick(seq_n);", clk_felucca, 1)

        # Sequencer note playback to MIDI OUT (allow sequencer notes always out on SMK-37)
        if "seq_out_on(" in seq_code:
            seq_code = re.sub(r'if\s*\(\s*!song\.g\[G_MIDI\]\s*\|\|\s*note\s*>\s*127u\s*\)', 'if (note > 127u)', seq_code)
        elif "0x90u | mc" not in seq_code and "seq_step(" in seq_code:
            seq_code = re.sub(
                r'trk_note_on\(t,\s*nn\[i\],\s*vv\[i\]\);',
                'trk_note_on(t, nn[i], vv[i]);\n#if BOARD_SMK37\n            uint32_t mc = trk_midi_ch(trk_index(t));\n            if (mc <= 15u) midi_out_event(0x09u | ((0x90u | mc) << 8) | ((uint32_t)nn[i] << 16) | ((uint32_t)vv[i] << 24));\n#endif',
                seq_code
            )
            seq_code = re.sub(
                r'trk_note_off\(t,\s*t->seq_notes\[i\]\);',
                'trk_note_off(t, t->seq_notes[i]);\n#if BOARD_SMK37\n            uint32_t mc = trk_midi_ch(trk_index(t));\n            if (mc <= 15u) midi_out_event(0x08u | ((0x80u | mc) << 8) | ((uint32_t)t->seq_notes[i] << 16));\n#endif',
                seq_code
            )

        if "smk_extkey_take" not in seq_code and "keyboard_block(void)" in seq_code:
            extkey_hook = '''static void keyboard_block(void)
{
#if BOARD_SMK37
    {
        int32_t ev;
        while ((ev = smk_extkey_take()) >= 0) {
            uint32_t ek = (uint32_t)(ev >> 8);
            uint32_t ev_vel = (uint32_t)(ev & 0xFF);
            track_t *t = TSEL;
            uint32_t mc = trk_midi_ch(trk_index(t));
            int32_t note = 48 + (int32_t)ek + (int32_t)song.octave * 12;
            if (note < 0) note = 0; else if (note > 127) note = 127;
            if (ev_vel) {
                input_on(t, (uint32_t)note, ev_vel);
                midi_out_event(0x09u | ((0x90u | (mc & 0x0Fu)) << 8) | ((uint32_t)note << 16) | ((uint32_t)ev_vel << 24));
            } else {
                input_off(t, (uint32_t)note);
                midi_out_event(0x08u | ((0x80u | (mc & 0x0Fu)) << 8) | ((uint32_t)note << 16));
            }
        }
    }
#endif'''
            seq_code = re.sub(r'static\s+void\s+keyboard_block\(void\)\s*\{', extkey_hook, seq_code, count=1)

        seq_c.write_text(seq_code, encoding="utf-8")

    # 9. Patch firmware/src/usb.c & midi_uart.c for TRS MIDI OUT
    usb_c = src_dir / "usb.c"
    if usb_c.exists():
        print("[*] 9/10 Patching firmware/src/usb.c & midi_uart.c for TRS MIDI OUT (PC7)...")
        usb_code = usb_c.read_text(encoding="utf-8")
        if "smk_midi.h" not in usb_code:
            usb_code = '#if BOARD_SMK37\n#include "smk_midi.h"\n#endif\n' + usb_code
        if "smk_trs_tx_byte" not in usb_code and "midi_out_event(uint32_t pkt)" in usb_code:
            trs_router = '''#if BOARD_SMK37
    uint8_t cin = (uint8_t)(pkt & 0x0Fu);
    uint8_t b1  = (uint8_t)((pkt >> 8) & 0xFFu);
    uint8_t b2  = (uint8_t)((pkt >> 16) & 0xFFu);
    uint8_t b3  = (uint8_t)((pkt >> 24) & 0xFFu);
    if (cin == 0x0Cu || cin == 0x0Du || (b1 >= 0xC0u && b1 <= 0xDFu)) {
        smk_trs_tx_byte(b1); smk_trs_tx_byte(b2);
    } else if (b1 >= 0x80u && b1 < 0xF8u) {
        smk_trs_tx_byte(b1); smk_trs_tx_byte(b2); smk_trs_tx_byte(b3);
    }
#endif
'''
            usb_code = re.sub(r'static void midi_out_event\(uint32_t pkt\)[^{]*\{', r'\g<0>\n' + trs_router, usb_code)
        usb_c.write_text(usb_code, encoding="utf-8")

    muart_c = src_dir / "midi_uart.c"
    if muart_c.exists():
        muart_code = muart_c.read_text(encoding="utf-8")
        if "#if BOARD_SMK37" not in muart_code:
            muart_code = re.sub(
                r'static void uart_midi_init\(void\)[^{]*\{',
                'static void uart_midi_init(void)\n{\n#if BOARD_SMK37\n    return;\n#endif',
                muart_code
            )
            muart_code = re.sub(
                r'static void uart_midi_poll\(void\)[^{]*\{',
                'static void uart_midi_poll(void)\n{\n#if BOARD_SMK37\n    return;\n#endif',
                muart_code
            )
            muart_c.write_text(muart_code, encoding="utf-8")

    # 10. Patch tools/build.py & tools/fm1pkg_make.py
    print("[*] 10/10 Updating build and packaging tools...")
    if (tools_dir / "fm1pkg_make.py").exists():
        melodee_pkg = (MELODEE_DIR / "tools" / "fm1pkg_make.py").read_text(encoding="utf-8")
        (tools_dir / "fm1pkg_make.py").write_text(melodee_pkg, encoding="utf-8")

    build_py = tools_dir / "build.py"
    if build_py.exists():
        txt = build_py.read_text(encoding="utf-8")
        if 'BOARD = os.environ.get("BOARD"' not in txt:
            txt = 'import os\nBOARD = os.environ.get("BOARD", "smk37")\n' + txt
        if 'if BOARD == "smk37":' not in txt:
            txt = txt.replace(
                'flags = [',
                'flags = []\n    if BOARD == "smk37":\n        flags += ["-DBOARD_SMK37=1", "-DFELUCCA_CDC=0", "-DFELUCCA_UART=0"]\n    flags += ['
            )
        build_py.write_text(txt, encoding="utf-8")

    # GitHub Actions workflow
    workflows_dir = target_repo_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    workflow_template = (BASE_DIR / "build-smk37.yml.txt").read_text(encoding="utf-8")
    (workflows_dir / "build-smk37.yml").write_text(workflow_template, encoding="utf-8")

    print("[+] Successfully ported repository to SMK-37!")
    print("    Ready to commit, push to GitHub, and build via GitHub Actions (Ubuntu x86_64).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 port_fm1_to_smk37.py <path_to_fm1_repo>")
        sys.exit(1)
    port_repo_to_smk37(Path(sys.argv[1]))
