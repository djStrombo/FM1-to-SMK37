# 04: Controls mapping

How each FM-1 control and its SLOOP function lands on the SMK-37 in the reference port (SLOOP's SMK-37 build). Use it as
a template for other firmwares. The FM-1 column and the SLOOP column hold for any SLOOP fork. For a Felucca fork,
replace the SLOOP column with the fork's own functions.

The rule behind the mapping: **every FM-1 control keeps a home on the SMK**, so the original manual still applies.
The SMK's extra controls (outer keys, faders, wheels, spare buttons) add to that and never replace it.

## Knobs, faders, wheels

| FM-1 (printed) | SLOOP function | SMK-37 (printed) | SLOOP on the SMK-37 |
|---|---|---|---|
| MASTER (pot, top left) | output volume | K1 | master volume (a virtual pot: 24 of 1024 steps per detent) |
| SELECT (large encoder) | tempo on the TRACKS screen, page left/right, visualiser style, menu section | K2 | SELECT: tempo, pages |
| ALGORITHM | select track 1..4 | K3 | track |
| PRESETS | sound (synth tracks), kit (drums) | K4 | sound, kit |
| KNOB 1 | on-screen dial 1 (blue) | K5 | dial 1 |
| KNOB 2 | on-screen dial 2 (green) | K6 | dial 2 |
| KNOB 3 | on-screen dial 3 (yellow) | K7 | dial 3 |
| KNOB 4 | on-screen dial 4 (orange) | K8 | dial 4 |
| none | | FADER 1..4 | tracks 1..4 (4 = drums). FADER BANK picks what they set: A level, B filter (left low-pass, centre open, right high-pass), C reverb send, D delay send. A fader takes over only once it is moved. |
| none (SLOOP has no wheels) | | PITCH wheel | pitch bend of the selected synth track, +-7 semitones |
| none | | MOD wheel | vibrato at 10 Hz, up to +-1 semitone (up = more) |
| none | | PEDAL jack | not used yet |

## Buttons

| FM-1 (printed) | SLOOP tap | SLOOP hold (layer) | SMK-37 (printed) | SLOOP on the SMK-37 |
|---|---|---|---|---|
| PLAY | start / stop (LED flashes on the beat) | | SEQ PLAY | PLAY |
| REC | record / arm | 2 s: clear track | SEQ REC | REC |
| HOME | TRACKS screen; again: visualiser | settings menu | PATCH | HOME |
| ENV | envelope pages | | CHORD | ENV |
| LFO | LFO pages | | NOTE REPEAT | LFO |
| FX | effect pages | punch-in effects on the keys | FX | FX |
| SEL | key and chord pages | key layer | SCALE | SEL (the key layer shows a piano layout on the pads) |
| EDIT | sound pages, drum kit | erase layer | PARA | EDIT |
| ARP | arpeggiator pages | note repeat (rolls) | ARP | ARP (LED lit while the selected track's arpeggiator runs) |
| SEQ | step and pattern pages | step layer (steps 1..16) | SEQ | SEQ |
| GLO | global, master, system | mix layer (mute, solo, fill, tap) | GLOBE | GLO |
| SAVE | song screen, save | song layer (slots A..D) | BT | SAVE (SLOOP has no Bluetooth) |
| OCT- | octave down | drums: ghost hits | OCTAVE- | OCT- |
| OCT+ | octave up | drums: hard hits | OCTAVE+ | OCT+ |
| none | | | KNOB BANK | free |
| none | | | FADER BANK | fader bank A, B, C, D (shown on screen; LED lit when not on A) |
| none | | | < | page back (like SELECT, never tempo). With SEQ held: step page back. On the visualiser: style. |
| none | | | > | page forward. With SEQ held: step page forward. On the visualiser: style. |

## Keys and pads

| FM-1 | SLOOP | SMK-37 | SLOOP on the SMK-37 |
|---|---|---|---|
| 27 keys F3..G5 | notes; in layers: tiles (steps, effects, mix, ...) | middle 27 keys F3..G5 | the same, with velocity |
| none | | lowest 5 keys C3..E3 | synth tracks: notes. Drum track: C3 kick, D3 snare, E3 hi-hat (a black key plays its left white neighbour). |
| none | | highest 5 keys G#5..C6 | synth tracks: notes. Drum track: G#5 cowbell, A5 open hi-hat, B5 crash, C6 ride. |
| LEDs under the 27 keys | what is on or playing | 16 RGB pads | the pads are the 16 **white** keys (as steps and tiles: top row 1..8, bottom row 9..16), with velocity. Lit in the screen's track colours (blue, green, yellow, orange): steps lit, playhead and hits bright, off is dark. SEL layer: piano layout. SAVE layer: used slots green, free slots white. |

White key to pad. Hardware pads 0..7 are the top row, 8..15 the bottom row ([01-hardware.md](01-hardware.md), 6.3).
The SMK-37 build uses two orders: as a step grid or tiles the pads read like text; as a keyboard the low notes are at the
bottom.

| White key | F3 | G3 | A3 | B3 | C4 | D4 | E4 | F4 | G4 | A4 | B4 | C5 | D5 | E5 | F5 | G5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Step grid, tiles | top 1 | top 2 | top 3 | top 4 | top 5 | top 6 | top 7 | top 8 | bottom 1 | bottom 2 | bottom 3 | bottom 4 | bottom 5 | bottom 6 | bottom 7 | bottom 8 |
| Hardware pad (grid) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
| Keyboard | bottom 1 | bottom 2 | bottom 3 | bottom 4 | bottom 5 | bottom 6 | bottom 7 | bottom 8 | top 1 | top 2 | top 3 | top 4 | top 5 | top 6 | top 7 | top 8 |
| Hardware pad (keyboard) | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |

Piano layout (on request of the UI): the top row plays C4 D4 E4 F4 G4 A4 B4 C5, and the bottom row the black keys
between them (C#4 D#4, gap, F#4 G#4 A#4, gap, C#5).

## Power-on and special combos

Unchanged from SLOOP on the FM-1. OCT- and OCT+ are the SMK's OCTAVE- and OCTAVE+.

| Combo | Does |
|---|---|
| OCTAVE- held at power-on | USB rescue mode |
| OCTAVE- + OCTAVE+ held at power-on | hardware calibration (re-teach which button and knob does what) |
| OCTAVE- + OCTAVE+ held 5 s while stopped | mask-ROM bootloader (UBOOT), for flash backups |

## Ideas not built yet

- KNOB BANK: switch K5..K8 to the page's next four parameters.
- A master effects bank for the faders.
- Pedal: sustain, or start/stop.
- Pad pressure (measured by the HAL, unused so far) as a modulation source.
- TRS MIDI OUT (UART1 on PC7).
