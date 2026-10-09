# FM-1 to SMK-37 Pro: porting custom firmware

A guide to running M-Vave FM-1 custom firmware on the **M-Vave SMK-37 Pro** keyboard.

The FM-1 has a lively open firmware scene. It started with
[Felucca](https://github.com/hugelton/Felucca) by Leo Kuroshita / Hügelton Instruments, and forks such as
[SLOOP](https://github.com/isod89/sloop-fm1), [sloopDX](https://github.com/zvenson/dxsloop),
[X0X](https://github.com/charlesvestal/fm1-x0x), [FoMni-1](https://github.com/charlesvestal/fm1-fomni) and
[Melodee](https://github.com/keremimo/melodee) followed. The SMK-37 Pro is a 37-key controller with 16 RGB pads,
8 encoders, 4 faders, pitch and mod wheels, a colour screen and a built-in synth. Inside it uses **the same JieLi
AC791N (WL82) chip** as the FM-1, the same second-stage bootloader, the same update loader and the same chip key.
Only the panel wiring is different.

So an FM-1 firmware can run on the SMK-37 Pro once you replace its board layer: the keyboard matrix, the
analog inputs, the display pins, the pad LEDs and the flash map. This guide documents that layer and shows how to
carry it over to any Felucca-family firmware.

Author: M. Geisler (makkuro).

## Reference implementation

[**Makkuro37**](https://github.com/genkigenki/Makkuro37) is a SLOOP-based firmware for the SMK-37 Pro, and it is
the working reference for this guide.

- `main` holds the full firmware: SLOOP plus the SMK board layer plus Makkuro37's own additions (boot intro,
  jingle, layout choices).
- **`smk37-board`** holds only the board port, as a patch series on top of SLOOP. It contains the board
  switch, flash map, update path, input HAL, display, pad LEDs, wheels and UI mapping. Apply this series when
  you port another firmware. [docs/03-porting-steps.md](docs/03-porting-steps.md) explains how.

## What can be ported

| Firmware | Base | Effort |
|---|---|---|
| SLOOP, sloopDX and other SLOOP forks | SLOOP | Low. The patch series was written against SLOOP 2.5, so most patches apply with `git am -3`. Conflicts appear mainly where the fork changed the UI code. |
| Felucca and its direct forks (X0X, FoMni-1, Melodee, Jangada, ...) | Felucca | Medium. The HAL patches carry over almost unchanged. Storage, the flash map and the UI mapping must be redone by hand against the fork's own files. |
| Firmware that does not use the Felucca HAL (`firmware/hal/fm1_*.h`) | other | High. Use [docs/01-hardware.md](docs/01-hardware.md) as a datasheet and write the board layer yourself. |

Expect about one evening for a SLOOP fork if you already have a working build setup. A Felucca fork with its own
storage layout takes a few days. Most of that time goes into the controls mapping, not the hardware.

## Safety first

The SMK-37 Pro has 1 MiB of flash. Some of it is **unique to your unit** and cannot be downloaded again:

| Flash range | Contents | Rule |
|---|---|---|
| `0x00000-0x03FFF` | flash header, second-stage bootloader, boot config | **never write** |
| `0xC0000-0xC0FFF` | BTIF: Bluetooth pairing data | **never write** |
| `0xC1000-0xC1FFF` | USRTRIM: factory key, pad and wheel calibration (`trimdat` record) | **never write** |
| `0xF4000-0xFDFFF` | USR: stock resources (kept so that a return to stock works) | do not write |
| `0xFF000-0xFFFFF` | key_mac: the chip's key and MAC data | **never write** |

If the stock firmware finds the calibration record missing, it writes default curves over it, and your unit's
factory key and pad tuning is gone for good. The reference port therefore uses an explicit allow-list of writable
flash ranges with compile-time checks, plus a second guard in the flash driver itself. Keep both in any port.

**Before you install anything, make a full flash backup.** In short:

1. Start an install of a custom SMK package. The stock firmware checks the package and restarts into the
   custom update loader. At this point the app area has not been rewritten yet.
2. Send the loader the soft key `F0 22 24 35 7D F7`. The keyboard restarts into the chip's mask-ROM
   bootloader (`WL82 UBOOT1.00`, a USB mass-storage device).
3. Read the full 1 MiB twice with [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool) and compare
   the two dumps. Check that the text `trimdat` sits at offset `0xC1224`.
4. Power-cycle the keyboard, then finish the install or go back to stock.

This path was verified on a real unit. The full procedure, recovery and rollback are in
[docs/02-update-and-recovery.md](docs/02-update-and-recovery.md).

**Rollback.** The stock SMK-37 Pro update package (`.fwsc`) can be installed again at any time through
M-Vave's own updater, or through the SLOOP-style installer once it understands the SMK's 36-block package
container. A custom firmware that follows this guide never touches the ranges above, so the stock firmware comes
back with its calibration intact.

You do all of this at your own risk. A port that ignores the flash rules can permanently damage your unit's
calibration.

## Contents

| File | What |
|---|---|
| [docs/01-hardware.md](docs/01-hardware.md) | The SMK-37 Pro hardware map compared with the FM-1: SoC, flash, display, pad LEDs, key matrix, velocity, buttons, encoders, ADC muxes, faders, wheels, pedal, battery, audio, MIDI out, USB |
| [docs/02-update-and-recovery.md](docs/02-update-and-recovery.md) | Update protocol, package format, full flash backup, install, recovery, return to stock |
| [docs/03-porting-steps.md](docs/03-porting-steps.md) | Step by step: source, patch series, conflicts, UI mapping, build, test on the device, install, rollback |
| [docs/04-controls-mapping.md](docs/04-controls-mapping.md) | FM-1 to SLOOP to SMK-37 Pro to Makkuro37 control tables |
| [docs/05-reverse-engineering.md](docs/05-reverse-engineering.md) | How the facts were obtained, and how to reproduce them with public tools |
| [AGENTS.md](AGENTS.md) | A condensed checklist for carrying out a port, written to be followed step by step |

Each fact in the hardware map is marked as either **verified** (checked on a real SMK-37 Pro) or **analysis**
(read from the stock firmware but not yet confirmed on hardware).

## Credits and links

This guide builds on the work of many people:

- [FM-1-RE](https://github.com/AL-255/FM-1-RE) by AL-255: the FM-1 reverse-engineering work this all builds on,
  and a large index of FM-1 firmwares and tools.
- [kagaimiq](https://github.com/kagaimiq): [jielie](https://github.com/kagaimiq/jielie) (JieLi chip
  documentation), [jl-misctools](https://github.com/kagaimiq/jl-misctools) (firmware package tools),
  [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool) (mask-ROM flash access) and
  [ghidra-jieli](https://github.com/kagaimiq/ghidra-jieli) (pi32v2 processor module).
- [Felucca](https://github.com/hugelton/Felucca) by Leo Kuroshita (@kurogedelic) / Hügelton Instruments: the
  open FM-1 firmware with its HAL, update loader and installer.
- [SLOOP](https://github.com/isod89/sloop-fm1) by isod89: the groovebox firmware the reference port is based on.
- SMK-37 Pro community documentation:
  [smk-37-pro-docs](https://github.com/jonathaslacerda/smk-37-pro-docs) by jonathaslacerda (manuals and stock
  firmware history) and [smk37-firmware-custom-mod](https://github.com/amalahama/smk37-firmware-custom-mod) by
  amalahama.
- FM-1 rescue dongles, for when the mask-ROM bootloader is not reachable by software:
  [FM-1 Transporter](https://github.com/kurogedelic/FM-1-transporter),
  [MvaveFM1Unbricker](https://github.com/Quixotic7/MvaveFM1Unbricker),
  [mvave-fm1-open-firmware](https://github.com/ip2k/mvave-fm1-open-firmware).
- The JieLi AC79 SDK (`fw-AC79_AIoT_SDK`, published by JieLi) for the SPI pin-group tables.

## License

The text and tables of this guide are licensed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). See [LICENSE](LICENSE).

The firmware code and patches this guide refers to (Felucca, SLOOP, Makkuro37 and the `smk37-board` patch
series) are **not** part of this repository. They are licensed under **GPL-3.0** in their own repositories, and
their licenses apply to them.

This repository contains no M-Vave or JieLi firmware, no flash dumps, no disassembly and no tools. M-Vave,
SMK-37 Pro and FM-1 are names of their respective owners. This project is not affiliated with M-Vave or JieLi.
