# AGENTS.md: porting playbook

This is a condensed, ordered checklist for porting an FM-1 firmware (Felucca family) to the M-Vave SMK-37 Pro.
It is written so that whoever carries out the port, a person or an automated coding tool, can follow it step by
step. Background and reasons are in [docs/](docs/). This file only says what to do and how to check it.

## Hard rules

1. **Flash.** No code path may erase or program `0x00000-0x03FFF`, `0xC0000-0xC1FFF`, `0xF4000-0xFDFFF` or
   `0xFF000-0xFFFFF`. Keep the explicit allow-list, the `_Static_assert`s and the second guard in the RAM flash
   driver from the reference series. Never widen them to make something work.
2. **FM-1 build.** Every change sits behind `BOARD_SMK37` (default 0). The FM-1 outputs (app binary, package,
   loader) must stay byte-identical. Check this after every area.
3. **Pins.** Never drive PB1 (charger status and 8 s reset pin). Never configure PH8 as UART RX, or PA9, PH6, PH8,
   PH9 as outputs (they are matrix rows). Keep PC9 an analog input.
4. **Hardware actions need the owner.** Installing, entering UBOOT and writing flash on a real unit happen only
   with the owner present and a verified full flash backup in hand
   ([docs/02-update-and-recovery.md](docs/02-update-and-recovery.md), section 3).
5. **No vendor material** goes into any repository: no stock firmware, dumps, disassembly or decompiled code.

## Inputs

- `FW`: the firmware repository to port (URL), and its base (SLOOP release or Felucca release).
- `REF`: `https://github.com/genkigenki/Snoop37.git`, branch `smk37-board` (the board patch series).
- A Linux or WSL2 shell with the JieLi toolchain and the AC79 SDK files the firmware's `BUILDING.md` asks for.

## Steps

### 1. Baseline

```sh
git clone "$FW" fw && cd fw
git config core.autocrlf false
sh build.sh
sha256sum build/*.bin build/*.fwsc build/loader/ota.bin > ../fm1-reference.sha256
sh tests/run_tests.sh || true      # record failures that exist before the port
```

Check: the build succeeds. Write down the pre-existing test failures.

### 2. Fetch the series

```sh
git remote add ref https://github.com/genkigenki/Snoop37.git && git fetch ref
git log --oneline --reverse <base>..ref/smk37-board
git format-patch <base>..ref/smk37-board -o ../smk37-patches
git switch -c smk37
```

`<base>` is the release the branch starts from (named in its first commit).

### 3. Apply area by area

```sh
git am -3 ../smk37-patches/*.patch
```

On a conflict, resolve it with the area table in [docs/03-porting-steps.md](docs/03-porting-steps.md),
section 4, then `git add` and `git am --continue`. If a patch does not fit the fork's structure, `git am --skip`
it and reimplement its intent by hand in a separate commit.

After the system patch (board switch, flash map, update path, package):

- `sh build.sh && sha256sum -c ../fm1-reference.sha256` passes.
- `BOARD=smk37 sh build.sh` builds a package with the identity `SMK-37 Pro_9xx`.
- The flash-map and loader tests pass for the SMK.

After the board-layer patches (input, LCD, pad LEDs):

- Both builds still pass the same checks.
- `grep -n "BOARD_SMK37" firmware/src/*.c` shows only the expected places: includes, identities, UI mapping,
  storage layout and console.

### 4. Storage for the fork's own objects

List every flash object the fork writes, with its FM-1 sector:

```sh
grep -rnE "0x[0-9A-Fa-f]{5}u?" firmware/src/storage.c firmware/src/eng_sample.c firmware/hal/fm1_flash*.h
```

Lay them out for the SMK inside `0x9D000-0xBAFFF` (store) and `0xC2000-0xE9FFF` (samples), with A/B sectors as
the fork uses them. Add a `_Static_assert` on the end address of each block. Check: the SMK flash-map test
passes and covers the new objects.

### 5. UI mapping

Follow [docs/03-porting-steps.md](docs/03-porting-steps.md), section 5, and
[docs/04-controls-mapping.md](docs/04-controls-mapping.md):

1. Middle 27 keys (keybed 5..31) become the FM-1 note keys, with velocity.
2. The 16 pads become the 16 white keys (top row = hardware pads 8..15).
3. Pad LEDs show what the FM-1 key LEDs showed.
4. Buttons and knobs by printed name. K1 is the virtual MASTER pot.
5. Then the extras: outer keys, faders, wheels.

If the fork stores a button map, give the SMK its own magic number. Check: host UI tests pass for both boards.

### 6. Build both boards

```sh
sh build.sh && sha256sum -c ../fm1-reference.sha256
BOARD=smk37 sh build.sh
sh tests/run_tests.sh             # no new failures compared with step 1
```

### 7. Device test (owner present, backup verified)

1. Install the SMK package with the fork's installer (it must accept `SMK` port names and the `SMK-37 Pro` model).
2. Turn on USB SERIAL (HOME menu, AUDIO; HOME is PATCH on the SMK), restart, open the serial console.
3. Work through the bring-up table in [docs/03-porting-steps.md](docs/03-porting-steps.md), section 7: `smk`,
   `padtest`, `leds`, keys, faders, wheels, saving and reloading a project.
4. Confirm that flash `0xC1224` still reads `trimdat`.

### 8. Deliver

- Commit messages describe the change. Push the branch.
- Document the SMK build command and the controls table in the fork's README.
- Release the `.fwsc` under the fork's license (GPL-3.0). Never attach stock files or dumps.

## Done when

- [ ] FM-1 build byte-identical to the baseline
- [ ] SMK build passes the host tests (no new failures)
- [ ] The flash allow-list and its asserts are unchanged or stricter
- [ ] The device checklist passes on a real unit
- [ ] The README documents the SMK build, the controls, the backup and the rollback
