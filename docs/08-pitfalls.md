# 08: Pitfalls

Things that went wrong in earlier ports, and the fix. Check this list before step 1 and again before a release.

## Flash and data

| Pitfall | Fix |
|---|---|
| A fork moved its flash map (Melodee 1.0's layout crosses the SMK's protected ranges). | Redesign the layout inside the allowed windows (store `0x9D000-0xBAFFF`, samples `0xC2000-0xE9FFF`). Never write `0x0-0x3FFF`, `0xC0000-0xC1FFF`, `0xF4000-0xFDFFF` or anything from `0xFF000`. Assert every block's end address. |
| Two firmwares read each other's flash data after a switch and misbehave. | Each firmware gets its own data family / owner tag (`FELUCCA_DATA_FAMILY` in the reference series). A store with another tag is treated as empty. |
| An upstream merge reuses a settings bit the port already uses (SLOOP 2.6's MIDI channel vs Snoop37's BOOT LOGO bits). | After every upstream merge, diff the settings struct and its bit masks. Move the port's bits to free space and migrate old values. |

## Identity, models and installers

| Pitfall | Fix |
|---|---|
| The SMK comes as SMK-37 Pro, SMK-37 Elite and MKE-P37; the stock updater only takes a unit's own model. | Build one package per model: `BOARD=smk37 MODEL=elite sh build.sh` (`pro`, `elite` or `mke`). Each reports its model's name, so the stock updater can restore the factory firmware. |
| Starrykey 37 Play's name, `STARRYKEY-37 PLAY` plus a version, is 21 characters; a package identity holds 20. | Use the SMK-37 Pro build on it. Installers accept any SMK model's package on any SMK model (never FM-1 to SMK or back). |
| The installer does not find a keyboard running another port. | Port-name filters must include every firmware's USB name. Add yours to the installers you ship. |
| Another firmware's identity reply ends its text early; string compares fail. | Parse identities up to the first NUL byte. |
| Windows shows MIDI ports as `MIDIIN2 (name)` and similar. | Match port names by substring, case-insensitive. |

## Build and tests

| Pitfall | Fix |
|---|---|
| Windows clones turn LF into CRLF; patches stop applying and hashes change. | `git config core.autocrlf false` before checkout (or clone with `-c core.autocrlf=false`). |
| `__DATE__` in the firmware makes builds differ from day to day. | Compare FM-1 hashes on the same day as the baseline, or pin the date for the build (`SOURCE_DATE_EPOCH` or a fixed define). |
| Font and image tools need a specific Pillow version. | Run the repository's tools in a Python virtual environment with the pinned versions. |
| Host tests on glibc fail on `clock_gettime` and friends with `-std=c99`. | `CC='cc -D_DEFAULT_SOURCE' sh tests/run_tests.sh` (some forks need `-D_GNU_SOURCE`). |

## Hardware

| Pitfall | Fix |
|---|---|
| Newer WS2812 parts need a longer reset than the stock firmware sends; a glitch shifts the chain and a pad lights its neighbour. | Send a long reset (about 250 bytes of zeros) before each pad LED frame. |
| Docs, comments and console texts disagreed on which row is which. | Verified on a unit: top row = hardware pads 0..7, bottom = 8..15, the same index for hits and LEDs ([01-hardware.md](01-hardware.md), 6.3). Convert in one place; check with `padtest` and `smk` at bring-up. |
| Two-colour button LEDs: one LED index is the other half of a neighbour (SEQ PLAY's red half). | Take LED indices from the reference series, confirmed on a unit. |
| The SMK gives no VBUS on its USB-C port. | USB host experiments need a powered hub or an external 5 V supply. |
| Faders and wheels are noisy near the ends. | A dead band of +-1 step, ends reachable; wheels self-calibrate from the power-on centre. |
