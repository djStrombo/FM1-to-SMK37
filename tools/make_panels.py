#!/usr/bin/env python3
"""Draw the SMK-37 Pro panel diagrams used by docs/06-mapping-patterns.md.

    python tools/make_panels.py [--bare] [OUTDIR]      (default: assets/panel)

Writes one SVG per mapping pattern plus panel.svg (every control named). --bare: without the legend
(for pages that set the text themselves). No dependencies.
Positions are measured on a top-view photo of the SMK-37 Pro (1600 x 899 px, body x 30..1578, y 138..748).
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

BG, BODY, DIM, DIMF, INK, MUTED = "#04060c", "#1d3550", "#2a3a52", "#0a1220", "#dff8ff", "#7f9bb0"
CY, MG, AM = "#3cf0ff", "#ff3cd2", "#ffb02a"
TRK = ["#287cff", "#1ecc70", "#ffc618", "#ff621a"]           # the screen's track colours (Snoop37)
FONT = "JetBrains Mono, Consolas, Menlo, monospace"

SW = 66.09                                                  # white key pitch
BLACK = [0, 1, 3, 4, 5, 7, 8, 10, 11, 12, 14, 15, 17, 18, 19]  # black key j sits right of white key j
WHITE_NAMES = [n + str(o) for o in (3, 4, 5) for n in "CDEFGAB"] + ["C6"]
BTN_ROW0 = ["ARP", "NOTE REPEAT", "SCALE", "CHORD", "GLOBE", "BT"]
BTN_ROW1 = ["PATCH", "PARA", "FX", "SEQ", "SEQ PLAY", "SEQ REC"]
SBX = [1227, 1285, 1342, 1400, 1457, 1514]


def controls():
    """id -> (kind, cx, cy, w, h, printed name)"""
    c = {"pitch": ("wheel", 84, 278, 55, 145, "PITCH"), "mod": ("wheel", 162, 278, 55, 145, "MOD"),
         "screen": ("screen", 300, 222, 124, 115, "SCREEN")}
    for i, (k, n) in enumerate([("kb", "KNOB BANK"), ("fb", "FADER BANK"), ("left", "<"), ("right", ">"),
                                 ("octdn", "OCT-"), ("octup", "OCT+")]):
        c[k] = ("btn", 323 if i & 1 else 270, 323 + (i >> 1) * 27, 48, 22, n)
    for i in range(8):
        c[f"k{i + 1}"] = ("knob", 453 + i * 94, 197, 60, 60, f"K{i + 1}")
    for i in range(16):                                     # p1..p8 top row (hardware pads 8..15), p9..p16 bottom (0..7)
        c[f"p{i + 1}"] = ("pad", 453 + (i % 8) * 94, 277 if i < 8 else 348, 74, 56, str(i + 1))
    for j in range(4):
        c[f"f{j + 1}"] = ("fader", 1222 + j * 96, 242, 75, 125, f"F{j + 1}")
    for i, n in enumerate(BTN_ROW0 + BTN_ROW1):
        c["b_" + n.lower().replace(" ", "")] = ("btn", SBX[i % 6], 352 if i < 6 else 380, 48, 21, n)
    return c


C = controls()
BARE = False


def keys(fill):
    """fill: {key index 0..36 (C3..C6): (colour, label)}"""
    out, wi = [], 0
    semis = []                                              # semitone -> ("w", white idx) / ("b", black j)
    for j in range(22):
        semis.append(("w", j))
        if j in BLACK:
            semis.append(("b", j))
    semis = semis[:37]
    whites, blacks = [], []
    for s, (kind, j) in enumerate(semis):
        col, lab = fill.get(s, (None, ""))
        if kind == "w":
            x = 78 + j * SW
            whites.append((x + 2, 462, SW - 4, 280, col, lab))
        else:
            x = 78 + (j + 1) * SW
            blacks.append((x - 20, 462, 40, 170, col, lab))
    for x, y, w, h, col, lab in whites:
        out.append(rect(x, y, w, h, col, 4))
        if lab:
            out.append(text(x + w / 2, y + h - 22, lab, 17, col or MUTED))
    for x, y, w, h, col, lab in blacks:
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{w}" height="{h}" rx="3" fill="{BG}"/>')
        out.append(rect(x, y, w, h, col, 3))
        if lab:
            out.append(text(x + w / 2, y + h - 14, lab, 13, col or MUTED))
    return out


def rect(x, y, w, h, col, r=4, sw=2.4):
    if col:
        return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{col}" '
                f'fill-opacity=".28" stroke="{col}" stroke-width="{sw}"/>')
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{DIMF}" stroke="{DIM}" stroke-width="1.6"/>'


def text(x, y, s, size=16, col=INK, anchor="middle", weight=600):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{col}" text-anchor="{anchor}">{escape(s)}</text>')


def control(cid, col=None, lab=None, bright=False):
    kind, cx, cy, w, h, name = C[cid]
    x, y, out = cx - w / 2, cy - h / 2, []
    if kind == "knob":
        if col:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="27" fill="{col}" fill-opacity=".28" stroke="{col}" stroke-width="2.4"/>')
        else:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="27" fill="{DIMF}" stroke="{DIM}" stroke-width="1.6"/>')
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + 14}" y2="{cy - 18}" stroke="{col or DIM}" stroke-width="2.4"/>')
        out.append(text(cx, cy - 36, lab if lab is not None else name, 19, col or MUTED))
    elif kind == "fader":
        out.append(f'<rect x="{cx - 4}" y="{y}" width="8" height="{h}" rx="3" fill="{DIMF}" stroke="{col or DIM}" stroke-width="1.6"/>')
        out.append(rect(cx - 30, cy - 11, 60, 22, col, 3))
        out.append(text(cx, y - 10, lab if lab is not None else name, 20, col or MUTED))
    elif kind == "wheel":
        out.append(rect(x, y, w, h, col, 10))
        for k in range(5):
            yy = y + 22 + k * 25
            out.append(f'<line x1="{x + 8}" y1="{yy}" x2="{x + w - 8}" y2="{yy}" stroke="{col or DIM}" stroke-opacity=".6" stroke-width="1.4"/>')
        out.append(text(cx, y + h + 24, lab if lab is not None else name, 18, col or MUTED))
    elif kind == "screen":
        out.append(rect(x - 8, y - 8, w + 16, h + 16, None, 6))
        out.append(rect(x, y, w, h, col, 2))
        if lab:
            for i, ln in enumerate(lab.split("\n")):
                out.append(text(cx, cy - 4 + (i - (len(lab.split(chr(10))) - 1) / 2) * 24, ln, 18, col or MUTED))
    elif kind == "pad":
        out.append(rect(x, y, w, h, col, 5, 3 if bright else 2.4))
        if bright and col:
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" rx="5" fill="{col}" fill-opacity=".55"/>')
        lines = (lab or "").split(chr(10))
        for i, s in enumerate(lines):
            if s:
                out.append(text(cx, cy + 7 + (i - (len(lines) - 1) / 2) * 20, s, 19 if len(s) < 6 else 15, INK if col else MUTED))
    else:                                                   # button
        out.append(rect(x, y, w, h, col, 3, 2))
        if lab:
            words, c2 = lab.split(" "), col or MUTED
            if cx < 400:                                    # the left cluster: labels beside it
                anchor, tx = ("end", x - 6) if cx < 300 else ("start", x + w + 6)
                for i, wd in enumerate(words):
                    out.append(text(tx, cy + 5 + (i - (len(words) - 1) / 2) * 14, wd, 14, c2, anchor))
            elif cy < 360:                                  # the top row of the grid: above
                for i, wd in enumerate(reversed(words)):
                    out.append(text(cx, y - 6 - i * 15, wd, 14, c2))
            else:                                           # the bottom row: below
                for i, wd in enumerate(words):
                    out.append(text(cx, y + h + 16 + i * 15, wd, 14, c2))
    return out


def panel(lit=None, keyfill=None, legend=(), title=None, names=False):
    """lit: {control id: (colour, label) or colour}; keyfill: see keys(); legend: [(colour, text)]"""
    lit = lit or {}
    legend = () if BARE else legend
    w, top = 1570, 128
    h_panel = 630
    h = h_panel + (44 * len(legend) + 20 if legend else 0) + (54 if title else 0)
    y0 = top - (54 if title else 0)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="20 {y0} {w} {h}" width="{w}" height="{h}">',
           f'<rect x="20" y="{y0}" width="{w}" height="{h}" fill="{BG}"/>']
    if title:
        out.append(text(44, y0 + 38, title, 26, INK, "start", 700))
    out.append(f'<rect x="30" y="138" width="1548" height="610" rx="26" fill="none" stroke="{BODY}" stroke-width="3"/>')
    out.append(f'<rect x="75" y="458" width="1460" height="288" rx="6" fill="none" stroke="{BODY}" stroke-width="1.6"/>')
    for cid, (kind, *_r, name) in C.items():
        v = lit.get(cid)
        col, lab, bright = (v, None, False) if isinstance(v, str) else (v + (False,))[:3] if v else (None, None, False)
        if names and lab is None:
            lab = name
        out += control(cid, col, lab, bright)
    out += keys(keyfill or {})
    if legend:
        ly = top + h_panel + 14
        for i, (col, s) in enumerate(legend):
            x, y = 50, ly + i * 44
            out.append(f'<rect x="{x}" y="{y}" width="28" height="28" rx="5" fill="{col}" fill-opacity=".45" stroke="{col}" stroke-width="2"/>')
            out.append(text(x + 44, y + 22, s, 26, INK, "start", 500))
    out.append("</svg>")
    return "\n".join(out) + "\n"


# --- the patterns -------------------------------------------------------------------------------------------------

def outer_keys(col_lo, col_hi, labels_lo=None, labels_hi=None):
    f = {}
    for i, s in enumerate([0, 1, 2, 3, 4]):
        f[s] = (col_lo, (labels_lo or [""] * 5)[i])
    for i, s in enumerate([32, 33, 34, 35, 36]):
        f[s] = (col_hi, (labels_hi or [""] * 5)[i])
    return f


def core_keys(col):
    return {s: (col, "") for s in range(5, 32)}


def patterns():
    P = {}
    # the full map
    lit = {}
    for i in range(16):
        hw = 8 + i if i < 8 else i - 8
        lit[f"p{i + 1}"] = (MG, f"{i + 1}" + chr(10) + f"hw {hw}")
    kf = core_keys(CY) | outer_keys(AM, AM)
    kf |= {0: (AM, "C3"), 5: (CY, "F3"), 31: (CY, "G5"), 36: (AM, "C6")}
    P["panel"] = panel(lit, kf, names=True, legend=[
        (CY, "middle 27 keys F3..G5 = the FM-1 keybed (velocity)"),
        (AM, "outer 10 keys C3..E3, G#5..C6: new"),
        (MG, "16 RGB pads: top row 1-8 = hardware pads 8..15, bottom 9-16 = 0..7")])

    # keys: the FM-1 range in the middle, the outer ten extend it
    kf = core_keys(CY) | outer_keys(AM, AM, ["kick", "", "snr", "", "hat"], ["cow", "", "oh", "crs", "ride"])
    P["keys-outer"] = panel({}, kf, legend=[(CY, "middle 27 keys = the FM-1 keybed (F3..G5)"),
                                            (AM, "outer 10: more notes; on a drum track: drums")])

    # pads: the 16 FM-1 white keys in reading order, track colours, playhead bright
    lit = {}
    on = {1, 4, 7, 10, 13, 15}
    for i in range(16):
        if i == 5:
            lit[f"p{i + 1}"] = ("#bfe6ff", str(i + 1), True)
        elif i in on:
            lit[f"p{i + 1}"] = (TRK[0], str(i + 1))
        else:
            lit[f"p{i + 1}"] = (None, str(i + 1))
    lit["screen"] = (TRK[0], "STEPS\ntrack 1")
    P["pads-steps"] = panel(lit, legend=[(TRK[0], "a step that is on, in its track's colour"),
                                         ("#bfe6ff", "playhead / hit: bright (pad 6)"),
                                         (DIM, "off is dark"), (CY, "read like text: steps 1-8 top, 9-16 bottom")])

    # pads: the sound picker
    lit = {f"p{i + 1}": (TRK[1], s) for i, s in enumerate(
        ["PNO", "EP", "ORG", "PAD", "STR", "BRS", "BELL", "PLK", "BASS", "SAW", "SQR", "FM", "VOX", "NOIS", "ACID", "SUB"])}
    lit["p3"] = (TRK[1], "ORG", True)
    lit["k4"] = (AM, "SOUND")
    lit["left"], lit["right"], lit["kb"] = (AM, "<"), (AM, ">"), (AM, "PIN")
    lit["screen"] = (TRK[1], "ORGAN\n3 / 16")
    P["pads-picker"] = panel(lit, legend=[(AM, "turn the sound knob: the pads show one kind"),
                                          (TRK[1], "tap a pad: pick and preview; < > page; a button pins it")])

    # pads: performance (voice gates, one CHAOS pad)
    vc = ["#ff4040", "#ff9614", "#ffe61e", "#46e646", "#14dcff", "#4678ff", "#aa5aff", "#ff5ad2"]
    lit = {f"p{i + 1}": (vc[i], f"V{i + 1}", i in (0, 3, 5)) for i in range(8)}
    lit["p16"] = (MG, "CHAOS", True)
    for i in range(8):
        lit[f"k{i + 1}"] = vc[i]
    P["pads-perform"] = panel(lit, legend=[(vc[3], "top pads: wake / sleep a voice (bright = sounding)"),
                                           (MG, "one pad for a big gesture: CHAOS"),
                                           (vc[6], "knob i = voice i (same colour on knob, pad and screen)")])

    # pads: strum plate, keys hold chords
    lit = {f"p{i + 1}": (AM, f"s{i + 1}", i in (2, 3, 4)) for i in range(16)}
    kf = {s: (CY, "") for s in range(5, 32)}
    kf[12] = (MG, "C")
    kf[16] = (MG, "E")
    kf[19] = (MG, "G")
    P["pads-strum"] = panel(lit, kf, legend=[(AM, "pads: 16 strings, top row low, bottom row high"),
                                             (MG, "keybed: hold a chord, then swipe across a row")])

    # pads: four 2x2 groups = the four corners, one parameter family each
    fam = [("#287cff", "SEL"), (AM, "MODE"), ("#aa5aff", "FILT"), ("#ff3c5a", "MUTE")]
    lit = {}
    for g, (col, n) in enumerate(fam):
        for r in range(2):
            for c in range(2):
                i = r * 8 + g * 2 + c
                lit[f"p{i + 1}"] = (col, f"{n} {r * 2 + c + 1}", (r * 2 + c) == 1)
    lit["screen"] = (CY, "1     2\n\n3     4")
    P["pads-xy"] = panel(lit, legend=[(fam[0][0], "each 2x2 group: corners 1 2 / 3 4 as on the screen"),
                                      (fam[1][0], "one group per job: select, mode, filter, mute"),
                                      (fam[2][0], "pad brightness = how loud that corner is now")])

    # faders: banks with soft takeover
    lit = {f"f{j + 1}": (TRK[j], f"T{j + 1}") for j in range(4)}
    lit["fb"] = (AM, "BANK")
    lit["k2"] = (AM, "A-D")
    lit["screen"] = (AM, "FADER BANK\nB: FILTER")
    P["faders-banks"] = panel(lit, legend=[(TRK[0], "fader i = track i, in the track colour"),
                                           (AM, "FADER BANK: A level, B filter, C reverb, D delay"),
                                           (CY, "a fader takes over only once it moves")])

    # faders: a fixed mixer / sends
    lit = {"f1": (CY, "REV"), "f2": (CY, "DLY"), "f3": (CY, "CHO"), "f4": (MG, "VOL"), "screen": (CY, "a bar\nover the view")}
    P["faders-mixer"] = panel(lit, legend=[(CY, "one job per fader, always the same"),
                                           (MG, "volume on the right, like a mixing desk")])

    # wheels
    lit = {"pitch": (MG, "BEND"), "mod": (MG, "MOD"), "screen": (MG, "BEND +3")}
    P["wheels"] = panel(lit, legend=[(MG, "pitch: bend (selected track); mod: vibrato or one macro"),
                                     (CY, "self-calibrating: centre at power-on, range widens, dead band")])

    # knobs: the FM-1 top row
    names8 = ["MASTER", "SELECT", "TRACK", "SOUND", "DIAL 1", "DIAL 2", "DIAL 3", "DIAL 4"]
    cols8 = [MUTED, CY, CY, CY] + TRK
    lit = {f"k{i + 1}": (cols8[i] if i else "#c8d6e0", names8[i]) for i in range(8)}
    lit["screen"] = (CY, "4 dials in\nthese colours")
    P["knobs"] = panel(lit, legend=[("#c8d6e0", "K1 = a virtual MASTER pot"),
                                    (CY, "K2-K4 = the FM-1's encoders, one step a detent"),
                                    (TRK[0], "K5-K8 = the screen's four dials, same colours")])

    # buttons: keep the printed meaning; the four extra ones
    pm = {"b_arp": "ARP", "b_noterepeat": "LFO", "b_scale": "SEL", "b_chord": "ENV", "b_globe": "GLO", "b_bt": "SAVE",
          "b_patch": "HOME", "b_para": "EDIT", "b_fx": "FX", "b_seq": "SEQ", "b_seqplay": "PLAY", "b_seqrec": "REC",
          "octdn": "OCT-", "octup": "OCT+"}
    lit = {k: (CY, v) for k, v in pm.items()}
    lit |= {"kb": (MG, "KNOB BANK"), "fb": (MG, "FADER BANK"), "left": (MG, "<"), "right": (MG, ">")}
    P["buttons"] = panel(lit, legend=[(CY, "the FM-1's 14 buttons: same job, printed name wins"),
                                      (MG, "4 extras: banks, < > pages")])

    # held button lends the knobs another job
    lit = {f"k{i + 1}": (AM, n) for i, n in enumerate(["ATK", "DEC", "SUS", "REL", "DET", "GLD", "STK", "STR"])}
    lit["b_chord"] = (AM, "HOLD")
    lit["screen"] = (AM, "VOICE\nK1-K8")
    P["knobs-hold"] = panel(lit, legend=[(AM, "hold a button: the 8 knobs get its 8 jobs"),
                                         (CY, "let go: back to the main set; the screen lists them")])
    return P


def main():
    global BARE
    args = [a for a in sys.argv[1:] if a != "--bare"]
    BARE = len(args) < len(sys.argv) - 1
    out = Path(args[0]) if args else Path(__file__).resolve().parent.parent / "assets" / "panel"
    out.mkdir(parents=True, exist_ok=True)
    for name, svg in patterns().items():
        (out / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
        print(out / f"{name}.svg")


if __name__ == "__main__":
    main()
