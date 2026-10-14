# 10: SMK-37 to FM-1 (the reverse port)

The rest of this kit ports an FM-1 firmware to the SMK-37. This page goes the other way: a firmware written for
the SMK-37 first (or grown there, like Vox37) gets an FM-1 target. The FM-1 is the smaller panel: fewer keys,
fewer controls, no pads, faders or wheels. The chip, the audio path, USB and the update protocol are the same, so
most of the work is the panel and the flash map. Read [01-hardware.md](01-hardware.md) for the two boards side by
side; this page lists what changes in the reverse direction and in what order.

## 1. The two panels

| Item | SMK-37 | FM-1 | What the FM-1 build does |
|---|---|---|---|
| Keys | 37, velocity (two contacts, factory curves at USRTRIM) | 27 (F3..G5), no velocity | Keys 5..31 of the SMK's keybed are the FM-1's keys 0..26. Use a fixed velocity (100). The outer 10 keys do not exist |
| Buttons | 18 (`smk_input.h` ids 0..17) | 14 (matrix ids 0..13: OCT- 0, OCT+ 1, FX 2, SEL 3, ENV 4, LFO 5, EDIT 6, GLO 7, HOME 8, SAVE 9, ARP 10, SEQ 11, PLAY 12, REC 13; Felucca's `panel.c` PANEL_DEFAULT) | Map by function, not by id. KNOB BANK, FADER BANK, <, >, PATCH, CHORD, NOTE REPEAT, PARA, BT, SCALE have no FM-1 button |
| Encoders | 8 (K1..K8), K1 a virtual MASTER pot | 7: SELECT 0, ALGORITHM 1, KNOB 1..4 2..5, PRESETS 6 | The FM-1's MASTER is a real pot (ADC, absolute 0..1023: smooth it and keep a dead band against the last bits). SELECT, ALGORITHM and PRESETS take what the SMK did with pads and arrows |
| LEDs | 19 button LEDs (two groups), 16 RGB pads (WS2812 on SPI1) | 14 button LEDs and 27 key LEDs, in column bitmaps (`fm1_led[col]`, `fm1_led_key(id)`: buttons 0..13, keys 14..40), a dim glow | Pad colours become button LEDs and the screen. Key LEDs can show notes, steps or a selection |
| Pads, faders, wheels, pedal | yes | none | Their jobs move to knob pages, buttons or the screen (section 3), or go |
| Matrix | 4 x 595 over SPI2 DMA, rows PA2, PA5..PA7, PA9, PH6, PH8, PH9 | 2 x 595 bit-banged, rows PA0, PA5..PA8, PB7 | Use `fm1_input.h` as it is: its tick, debounce and encoder decoder are the FM-1's |
| Frames | 625 a second | 909 a second | Count time in milliseconds, never in frames |
| Display | ST7789 240 x 240, SPI1 group A, no backlight pin | ST7789 240 x 240 (a row offset in its init), SPI1 group B, CS PC7, D/C PC8, backlight PA2 | `lcd.c` keeps both init tables by board. Keep the FM-1's LCD clock unless measured on a unit |
| ADC | `0x400D` timing (~40 us) | `0xF04E` / `0xF06E` timing, MASTER and the battery | Use `fm1_adc.h` on the FM-1; the SMK timing stays SMK only |
| MIDI | USB only (PH8 is a matrix row) | USB, and TRS MIDI IN on UART1 / PH8 | TRS MIDI IN may come back on the FM-1 build (`FELUCCA_UART`) |
| Flash part | JEDEC 0xEB6014 | JEDEC 0x856014 | `FL_JEDEC_OK` per board |

## 2. Flash map, identity, packages

| Item | SMK-37 | FM-1 |
|---|---|---|
| App area (PRCT) | `0x04000-0x9CFFF` | `0x04000-0x92FFF` (app slot 0x8DFBC) |
| The firmware's store | `0x9D000-0xBAFFF` (owner tag 0xAF000) | Felucca's: `0x97000-0xDFFFF`; settings `0xFC000-0xFEFFF` |
| Update staging | `0xBB000-0xBFFFF` | `0xE0000-0xE4FFF` (record at 0xE4F00) |
| Autosave and friends | inside the store window | `0xE5000-0xE7FFF` |
| Never written | `0x0-0x3FFF`, `0xC0000-0xC1FFF`, `0xF4000-0xFDFFF`, `0xFF000-` | `0x0-0x3FFF`, `0xE8000-0xFBFFF` (the stock OTA's VM backup, BTIF, USR), `0xFF000-` |
| Package identity | `SMK-37 Pro_9XY` (Elite, MKE-P37: their names) | `FM-1_9XY` |
| Update record | `ota-SMK-37 Pro_016` | `ota-FM-1_015` |
| Package | 36-block stock layout, SMK region table | 20-block, the FM-1 region table |

- Take the FM-1 half of `fm1_flash_map.h` and `fm1pkg_make.py`'s FM-1 table as they are. An object the SMK build
  keeps at an SMK address gets an FM-1 address inside the FM-1 windows, never an exception to the guard.
- The SMK's owner tag has no FM-1 counterpart (`st_owner_check` is empty there): two firmwares on one FM-1 meet
  each other's records in the same objects. Give every record a magic, a size, a version and a check sum, and treat
  anything else as empty.
- Build the FM-1's update loader without the SMK flag: the FM-1 loader stays byte-identical to the upstream one.
- Installers: an FM-1 package never on an SMK and an SMK package never on an FM-1, on every path (install and
  resume; AGENTS.md hard rule 9). Add the firmware's USB name to the installers' port filters.

## 3. What the SMK's extras become

| SMK-37 | FM-1 | Notes |
|---|---|---|
| Pads as choosers (modes, kits, sounds) | ALGORITHM or PRESETS (one detent a choice), the screen showing the list | The chooser's state on the screen; a key LED or a button LED for the one in use where it helps |
| Pads as memories (tap load, hold save) | PRESETS points at a memory (turning loads it), SAVE held 1 s saves into it | Show the memory number and whether it is empty |
| Pads held as effects (RECORD, ECHO, stutter) or toggled (PLAY) | Buttons held or tapped (REC, PLAY, ARP, ...) | Their LEDs lit while held or on |
| Faders (absolute, soft takeover) | A second or third page of KNOB 1..4, switched with SEL (and SELECT), HOME back to the first | The page's name on the screen; relative knobs need no takeover |
| Wheels | Dropped, or a knob on a page | MIDI pitch bend and CC1 still arrive over USB |
| Outer keys, velocity | Dropped; a fixed velocity | |
| K1 virtual MASTER | The MASTER pot | Read it before the audio starts (no jump at power-on) |
| < and > (pages, memories) | SELECT / PRESETS | |
| SMK-only button combos (< + > held) | Two free FM-1 buttons (for example ENV + LFO) | Keep OCT- + OCT+ held 5 s for UBOOT on both |
| RGB pad colours | Button LEDs and the screen | |

Keep the screen the same on both boards (240 x 240 on both): only the cells or labels that name a control change
(SMK "K5" becomes FM-1 "1" for KNOB 1, and so on).

## 4. Steps

1. **Board switch.** One flag (`BOARD_SMK37` 0 / 1) and, when the repository's FM-1 build must stay the upstream
   firmware, a separate build target for the FM-1 port of the new firmware (Vox37: `BOARD=fm1vox`, the FM-1
   layout and identity, its own compilation unit; `BOARD=fm1` still builds Felucca byte for byte).
2. **HAL.** Include `fm1_input.h` and `fm1_adc.h` instead of `smk_input.h`; drop the SMK-only parts (pad LEDs, trim
   curves, the SMK LCD clock). Grep the shared sources for `smk_`, `SMK_`, `fm1_in.pad`, `fm1_in.fader`,
   `fm1_in.wheel`, `fm1_in.keys`, `key_vel` and `padled` and give each an FM-1 path.
3. **Panel file.** Put each board's input and LED code in its own file (Vox37: `vo_panel_smk.c`,
   `vo_panel_fm1.c`) with the same small interface: read the controls, call the shared actions (set a value, load,
   save, open a page), light the LEDs, name the screen's cells. Shared actions and the screen stay in one file.
4. **Storage.** FM-1 addresses for every object (section 2), a record you can recognise, the guard unchanged.
5. **Identity.** `FM-1_900` (release `FM-1_9XY`), the USB names the firmware's.
6. **Tests.** A host test of the FM-1 panel against a stubbed `fm1_in` (buttons, encoder steps, notes, LED
   writes); render the FM-1 screens. Run the SMK tests too: the split must not change the SMK build's behaviour.
7. **Build both.** SMK packages, then the FM-1 package, then (last) the upstream FM-1 build for the test suite
   (both write the same `build/` intermediates, see [07-develop-for-both.md](07-develop-for-both.md)).

## 5. Pitfalls

| Pitfall | Fix |
|---|---|
| Code reads `fm1_in` fields the FM-1 input lacks (`keys`, `key_vel`, `pad_st`, `fader`, `wheel`). | Board-specific readers in the panel file; the shared code asks the panel. |
| SMK button ids used as numbers (10 GLOBE, 14 FX) in shared code. | Name them in the panel file; the FM-1's ids are different (FX 2, GLO 7). |
| LED code writes `fm1_led[id]` as an array of 19 on/off bytes (SMK). | On the FM-1 `fm1_led[]` holds column bitmaps: use `fm1_led_key(id, on)`. |
| A virtual pot's stored value (SMK K1) restored over the FM-1's real MASTER pot. | Store it only on the SMK; the FM-1 reads its pot. |
| The SMK store's owner-tag notice ("NEW STORE") or other SMK-only symbols in the main loop. | Guard them; the FM-1 has no owner tag. |
| Timing in frames (625 / s on the SMK, 909 / s on the FM-1). | Milliseconds. |
| The SMK's 20 MHz LCD clock carried over. | Keep the FM-1's 12 MHz until measured on a unit. |
| A USB host feature (a microphone) assumed to work on the FM-1. | Same chip and port, but untested: mark it experimental, keep device mode (the update path) the default whenever a computer is there. The SMK gives no VBUS to a device; the FM-1's port is unmeasured. |
| An SMK package offered to an FM-1 (or the reverse) by an installer path that skips the model check. | The model check on every path, with tests. |
| The repository's FM-1 build changes (a new flag, a shared file edited without a guard). | A separate target for the new firmware's FM-1 build; compare the upstream FM-1 hashes. |

## 6. Worked example: Vox37 on the FM-1

`BOARD=fm1vox sh build.sh` builds `vox37-fm1.fwsc` (identity `FM-1_900`, the FM-1's layout and update loader).
The screen is the SMK's; the panel is `firmware/src/vo_panel_fm1.c`; the host test `tests/vo_fm1.c`.

| SMK-37 | FM-1 |
|---|---|
| K1 MASTER | MASTER pot |
| Top pads 1..4: the modes | ALGORITHM |
| Bottom pads 1..8: the memories (tap / hold 1 s) | PRESETS (turn: load), SAVE held 1 s: save |
| K2..K8, faders 1..4 | KNOB 1..4 on three pages: MAIN (VOICE BLEND TONE COLOR), SOUND (WAVE TIMBRE SHAPE), MORE (HISS VOL RELEASE ENSEMBLE SPACE); SEL / SELECT the page, HOME the first |
| Pad 7 RECORD (held), pad 8 PLAY (tap; held + < >: the playback), pad 6 ECHO (held) | REC held, PLAY (held + SELECT: the playback), ARP held |
| FX HISS, OCTAVE- / + | FX, OCT- / OCT+ |
| GLOBE MIC SETUP (K5..K8, pad 5 RESET) | GLO (KNOB 1..4, EDIT RESET) |
| < + > held 3 s: USB host | ENV + LFO held 3 s |
| Wheels | dropped (MIDI bend and CC1 still work) |
| 37 velocity keys | 27 keys, velocity 100; their LEDs light the notes held |

The USB microphone on the FM-1 is untested.

## Checklist

- [ ] One flag; the repository's own FM-1 build unchanged (hashes), the new firmware's FM-1 build a separate target
- [ ] `fm1_input.h` / `fm1_adc.h` on the FM-1; no SMK HAL, pad LEDs, trim curves or SMK LCD clock in it
- [ ] Every SMK-only control has an FM-1 home (section 3) or is dropped on purpose; no control repeats another
- [ ] MASTER from the pot; key velocity fixed; time in milliseconds
- [ ] Every stored object at an FM-1 address inside the FM-1 windows; the guard unchanged; records recognisable
- [ ] Identity `FM-1_9XY`, the FM-1 update loader byte-identical, the 20-block FM-1 package
- [ ] Installers refuse an FM-1 package on an SMK and the reverse, on every path
- [ ] Host test of the FM-1 panel; FM-1 screens rendered; the SMK tests still pass
- [ ] Features the FM-1 cannot test yet (a USB host device) marked experimental in the README
