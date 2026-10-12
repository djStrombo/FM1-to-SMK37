# AGENTS.md: porting playbook

The ordered checklist for porting an FM-1 firmware (Felucca family) to the M-Vave SMK-37 Pro. Written for a
coding agent working with the owner of the keyboard: the agent writes code, the owner decides and handles the
hardware. Background is in [docs/](docs/). This file says what to do, in which order, and how to check it.

## Hard rules

Break none of these, even when the owner seems to ask for it. If a rule blocks you, stop and explain why.

1. **Protected flash.** No code path may erase or program `0x00000-0x03FFF`, `0xC0000-0xC1FFF`,
   `0xF4000-0xFDFFF` or `0xFF000-0xFFFFF`. Keep the allow-list, the `_Static_assert`s and the second guard in the
   RAM flash driver from the reference series. Never widen them to make something work. A fork that moved its
   flash map gets a new layout inside the allowed windows (step 3), never an exception.
2. **FM-1 build byte-identical.** Every change sits behind `BOARD_SMK37` (default 0). The FM-1 app binary,
   package and loader stay byte-identical to the baseline. Check after every area, not only at the end.
3. **Pins.** Never drive PB1 (charger status, 8 s reset). Never configure PH8 as UART RX, or PA9, PH6, PH8, PH9
   as outputs (matrix rows). Keep PC9 an analog input.
4. **The owner does all hardware actions.** The agent never opens a COM or MIDI port to install, never runs an
   installer, UBOOT or flash tool against a unit, and never asks the owner to skip the backup. Installing starts
   only after the owner confirms a verified full flash backup
   ([docs/02-update-and-recovery.md](docs/02-update-and-recovery.md), section 3).
5. **Return to stock stays possible.** Each package carries its model's identity (step 7), so M-Vave's updater
   still accepts the factory firmware afterwards. The firmware writes its own data family / owner tag, so two
   firmwares never misread each other's flash data.
6. **No vendor material** in any repository: no stock firmware, dumps, disassembly or decompiled code. No local
   paths, port names, serial numbers or e-mail addresses in docs, logs or commits you publish.
7. **No guessing on the panel.** Every mapping decision comes from the owner's answers in `smk37-port.yaml`.
   If something is not decided there, ask.

## Inputs

- `FW`: the firmware repository to port (URL) and its base (SLOOP or Felucca release).
- `REF`: `https://github.com/genkigenki/Snoop37.git`, branch `smk37-board` (the board patch series, on SLOOP 2.5).
- A Linux or WSL2 shell with the JieLi toolchain and the AC79 SDK files the firmware's `BUILDING.md` asks for.

## 0. Ask the owner

Before any code, ask these questions, a few at a time, and offer the patterns from
[docs/06-mapping-patterns.md](docs/06-mapping-patterns.md) as choices. Copy [smk37-port.yaml](smk37-port.yaml)
into the firmware repository, fill it from the answers, show it, and get an OK.

1. Which firmware, and which of its features matter most on the SMK?
2. The 16 pads: steps, instrument / sound picker, performance (voices, strum) or something else?
3. The 4 faders: mixer, filter, macros, banks of these?
4. The 10 outer keys (C3-E3, G#5-C6): extend the range, drums on a drum track, transpose, or off?
5. Pitch wheel and mod wheel: bend and vibrato, or a performance macro? Bend range?
6. Knobs K1-K8: the FM-1's top row (K1 = MASTER) or your own layout?
7. Screen: keep the FM-1 UI, or redesign it for the bigger panel? Colours?
8. Name, boot logo, credit line, USB port name.
9. Models: SMK-37 Pro, SMK-37 Elite, MKE-P37, Starrykey 37 Play (uses the Pro build)?
10. Delivery: own fork and release, an upstream pull request, or both?

Filled example: [examples/snoop37.yaml](examples/snoop37.yaml).

## 1. Baseline

```sh
git clone "$FW" fw && cd fw
git config core.autocrlf false
sh build.sh
sha256sum build/*.bin build/*.fwsc build/loader/ota.bin > ../fm1-reference.sha256
sh tests/run_tests.sh || true      # record failures that exist before the port
```

Check: the build succeeds. Write down the pre-existing test failures and the toolchain versions. Builds embed
`__DATE__`: compare hashes on the same day, or pin the date (see [docs/08-pitfalls.md](docs/08-pitfalls.md)).

## 2. Apply the series, area by area

```sh
git remote add ref https://github.com/genkigenki/Snoop37.git && git fetch ref
git log --oneline --reverse <base>..ref/smk37-board
git format-patch <base>..ref/smk37-board -o ../smk37-patches
git switch -c smk37
git am -3 ../smk37-patches/*.patch
```

On a conflict, resolve it with the area table in [docs/03-porting-steps.md](docs/03-porting-steps.md),
section 4, then `git add` and `git am --continue`. If a patch does not fit the fork, `git am --skip` it and
reimplement its intent by hand in a separate commit. After each area:

- `sh build.sh && sha256sum -c ../fm1-reference.sha256` passes.
- `BOARD=smk37 sh build.sh` builds a package with the identity `SMK-37 Pro_9xx`.
- The tests show no new failures; the flash-map and loader tests pass for the SMK.
- `grep -n "BOARD_SMK37" firmware/src/*.c` shows only the expected places.

Stop and report to the owner after the system patch and after the board-layer patches.

## 3. Storage

List every flash object the fork writes, with its FM-1 sector:

```sh
grep -rnE "0x[0-9A-Fa-f]{5}u?" firmware/src/storage.c firmware/src/eng_sample.c firmware/hal/fm1_flash*.h
```

Lay them out for the SMK inside `0x9D000-0xBAFFF` (store) and `0xC2000-0xE9FFF` (samples), with A/B sectors
as the fork uses them. Give the firmware its own data family / owner tag. Add a `_Static_assert` on the end
address of each block. Check: the SMK flash-map test passes and covers the new objects.

## 4. Mapping

Implement `smk37-port.yaml`, using the patterns in [docs/06-mapping-patterns.md](docs/06-mapping-patterns.md).
Default order:

1. Middle 27 keys (keybed 5..31) = the FM-1 note keys, with velocity from the unit's factory curves.
2. The 16 pads as decided (default: the FM-1's 16 white keys in reading order, top row = hardware pads 8..15).
3. Pad LEDs show what the FM-1 key LEDs showed, in the screen's colours.
4. Buttons and knobs by printed name; K1 is the virtual MASTER pot; one encoder step per detent.
5. The extras: outer keys, faders (soft takeover), wheels (self-calibrating).
6. The screen rules: the screen shows what you touch first, same colours and places as the panel, no hidden modes.

If the fork stores a button map, give the SMK its own magic number. Write the controls table (`docs/SMK37.md` or
`docs/CONTROLS.md`) as you go. Check: host UI tests pass for both boards.

## 5. Build both

```sh
sh build.sh && sha256sum -c ../fm1-reference.sha256
BOARD=smk37 sh build.sh
sh tests/run_tests.sh             # no new failures compared with step 1
```

Keep SMK code in board files and `#if BOARD_SMK37` blocks. See [docs/07-develop-for-both.md](docs/07-develop-for-both.md).

## 6. Device loop with the owner

The owner installs; the agent reads what the owner reports. Repeat until it plays well:

1. Hand over the package path, its SHA-256 and what changed. The owner installs with the fork's installer
   (Python or web), after the backup.
2. The owner turns on USB SERIAL (HOME menu, AUDIO; HOME is PATCH on the SMK), restarts, and opens the console.
   Ask for `status`, `smk`, `padtest`, `leds` and the log lines around a problem.
3. Work through the bring-up table in [docs/03-porting-steps.md](docs/03-porting-steps.md), section 7: keys,
   pads, faders, wheels, saving and reloading a project.
4. The owner plays and reports. Fix, rebuild both boards, re-run the tests, hand over again.
5. Confirm with the owner that flash `0xC1224` still reads `trimdat`.

## 7. Per-model builds

```sh
BOARD=smk37 MODEL=pro   sh build.sh   # SMK-37 Pro, also for Starrykey 37 Play
BOARD=smk37 MODEL=elite sh build.sh   # SMK-37 Elite
BOARD=smk37 MODEL=mke   sh build.sh   # MKE-P37
```

Each package reports its model's name, so the stock updater can restore that model's factory firmware. The
installer's port-name filters must include this firmware's USB name. Parse identities to the first NUL.

## 8. Deliver

- **Own release:** a README with the build commands, the controls table, the backup and the rollback, and the
  `.fwsc` per model under the fork's license (GPL-3.0). Never attach stock files or dumps.
- **Upstream pull request:** one clean commit behind `BOARD_SMK37`, branding removed, `docs/SMK37.md` with the
  controls. The PR text says the FM-1 build is unchanged and offers to maintain the target or split the commit.
- Commit messages describe the change. The owner pushes and publishes.

## Done when

- [ ] `smk37-port.yaml` filled and approved by the owner
- [ ] FM-1 build byte-identical to the baseline
- [ ] SMK build passes the host tests (no new failures)
- [ ] The flash allow-list and its asserts are unchanged or stricter
- [ ] The device checklist passes on a real unit (owner confirmed)
- [ ] One package per model, each with its model's identity
- [ ] The README documents the SMK build, the controls, the backup and the rollback
