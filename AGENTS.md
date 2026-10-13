# AGENTS.md: porting playbook

The ordered checklist for porting an FM-1 firmware (Felucca family) to the M-Vave SMK-37. Written for a
coding agent working with the owner of the keyboard: the agent writes code, the owner decides and handles the
hardware. Background is in [docs/](docs/). This file says what to do, in which order, and how to check it.

## Hard rules

Break none of these, even when the owner seems to ask for it. If a rule blocks you, stop and explain why. These
rules win over the firmware's own agent files (`CLAUDE.md`, `AGENTS.md`), for example an "auto-merge" rule.

1. **Protected flash.** No code path may erase or program `0x00000-0x03FFF`, `0xC0000-0xC1FFF`,
   `0xF4000-0xFDFFF` or `0xFF000-0xFFFFF`. Keep the allow-list, the `_Static_assert`s and the second guard in the
   RAM flash driver from the board layer. Never widen them to make something work. An object whose FM-1 address
   falls in a protected range moves (step 3), never gets an exception.
2. **FM-1 build byte-identical.** Every change sits behind `BOARD_SMK37` (default 0). The FM-1 app binary,
   package and loader stay byte-identical to the baseline, and the FM-1 path gets no new compiler flag. Check after
   every area, not only at the end.
3. **Pins.** Never drive PB1 (charger status, 8 s reset). Never configure PH8 as UART RX, or PA9, PH6, PH8, PH9
   as outputs (matrix rows). Keep PC9 an analog input.
4. **The owner does all hardware actions.** The agent never opens a COM or MIDI port to install, never runs an
   installer, UBOOT or flash tool against a unit, and never asks the owner to skip the backup. Installing starts
   only after the owner confirms a verified full flash backup
   ([docs/02-update-and-recovery.md](docs/02-update-and-recovery.md), section 3).
5. **Return to stock stays possible.** Each package carries its model's identity (step 7), so M-Vave's updater
   still accepts the factory firmware afterwards.
6. **Git stays with the owner.** Work on a branch `smk37`. Never merge, push, tag or open a pull request without
   the owner's OK. An upstream pull request changes sources only: never the live site or generated directories
   (for example `docs/` when the maintainer publishes it from `web/` with `make_site.py`).
7. **No vendor material** in any repository: no stock firmware, dumps, disassembly or decompiled code. No local
   paths, port names, serial numbers or e-mail addresses in docs, logs or commits you publish.
8. **No guessing on the panel.** Every mapping decision comes from the owner's answers in `smk37-port.yaml`.
   If something is not decided there, ask.
9. **Installers check the model on every path.** Once an installer accepts SMK loaders (`ota-SMK-37 Pro_9XX`), its
   resume path (device already in update mode, then write) checks the loader's model against the package being
   written, by the same rule as `install()` (model equality or the same-keyboard rule). Without the package's
   identity it writes nothing. Cover both cases with a test.

## The goal: an upstream pull request

A port of someone else's firmware is a pull request to that firmware, not a new product.

- **Same name, same look.** The SMK-37 build keeps the project's name, logo and boot. No porter credit or branding
  on screen, no renamed product ("xxx37"). Packages are named `<project>-smk37.fwsc`, `<project>-smk37-elite.fwsc`,
  `<project>-smk37-mke.fwsc`.
- **All models from the start:** `MODEL=pro|elite|mke` (step 7).
- **`SMK37.md`** at the top level, neutral: models, controls table, build (with `MODEL=pro|elite|mke`), install
  with `tools/fm1_install.py`, the way back with M-Vave's M-UPGRADE, safety. The README gets one line:
  `**M-Vave SMK-37:** see [SMK-37 instructions](SMK37.md).` Optional, in `SMK37.md`: "Until this project's
  releases include SMK-37 packages, unofficial builds can be installed with the web installer: <url>".
- **Copyright lines** of new SMK files name the porter, e.g. `M. Geisler (genkigenki/makkuro)` (format only).
- **Hosting until merged:** a real GitHub fork of the original, with its releases there. One fork per fork network:
  Felucca-family forks share the porter's Felucca fork, one branch per project (`<project>-smk37`). Archive it once
  the PR is merged.
- **PR text** (step 8): what it adds, the FM-1 build unchanged (byte-identical), the tests, what was tested on a
  unit and what was not. End with something like "I hope you'd like to take it in; I'm glad to change anything
  you'd like first."

A new firmware of the owner's own (like Makkuro37) is free in name and look.

## Inputs

- `FW`: the firmware repository to port (URL).
- The board layer, by the firmware's base (step 1):

  | Base | Board layer | How |
  |---|---|---|
  | SLOOP (and its forks) | `https://github.com/genkigenki/sloop-fm1.git`, branch `smk37` (= isod89/sloop-fm1#112): the commits on SLOOP 2.6 `8fad1a1` | `git cherry-pick -x 8fad1a1..ref/smk37` |
  | SLOOP 2.5 forks | the archived `https://github.com/genkigenki/Snoop37.git`, branch `smk37-board` (a patch series on SLOOP 2.5) | `git am -3` |
  | Felucca (and its forks) | `https://github.com/genkigenki/Felucca.git`, branch `smk37` (= hugelton/Felucca#237): the commits on Felucca 1.6 `1727537` (SMK-37 target, emulator fix, `SMK37.md`, neutral names, Elite / MKE `MODEL` builds, copyright lines) | `git cherry-pick -x 1727537..ref/smk37` |
  | other | [docs/01-hardware.md](docs/01-hardware.md) as the datasheet, the Felucca commits as the model | by hand |

  Older Felucca forks: the branches `rainbow-smk37` (a 1.1.5 fork) and `ghoulbox-smk37` (a 1.4.1 fork) on
  genkigenki/Felucca are worked examples of the same layer on an older base.

- A Linux or WSL2 shell with the JieLi toolchain, the AC79 SDK files and Pillow with raqm
  ([docs/03-porting-steps.md](docs/03-porting-steps.md), section 0). On Windows run every build and test inside
  WSL, not in Git Bash.

## 0. Ask the owner

Before any code, ask these questions, a few at a time, and offer the patterns from
[docs/06-mapping-patterns.md](docs/06-mapping-patterns.md) as choices. Copy [smk37-port.yaml](smk37-port.yaml)
into the firmware repository, fill it from the answers, show it, and get an OK.

1. Which firmware, and which of its features matter most on the SMK?
2. The 16 pads: steps, instrument / sound picker, performance (voices, strum) or something else?
3. The 4 faders: mixer, filter, macros, banks of these, or what has no direct control yet?
4. The 10 outer keys (C3-E3, G#5-C6): extend the range, drums on a drum track, transpose, or off?
5. Pitch wheel and mod wheel: bend and vibrato, or a performance macro? Bend range?
6. Knobs K1-K8 and the 18 buttons: keep the firmware's own layout and names, or remap? What do KNOB BANK,
   FADER BANK, `<` and `>` do?
7. May a control repeat another one's job? (Default: no doubles.)
8. Screen: keep the firmware's UI, or redesign it for the bigger panel? Colours?
9. USB port name (keep the firmware's). Name, logo and boot stay the project's (see "The goal" above).
10. Flash data: its own data family (1..7 of A-Z 0-9, e.g. `GHOULBX`; other firmwares' data is cleared on a
    switch, and its own on a switch back), or share the upstream family (data survives switching between the two)? Share only if the settings layouts
    match byte for byte: check for "unused" settings bytes the fork borrowed and the upstream uses later.
11. Models: SMK-37 Pro, SMK-37 Elite, MKE-P37 (all three by default), Starrykey 37 Play (uses the Pro build).
12. Delivery: an upstream pull request (the default for someone else's firmware), hosted in a fork until merged.
13. Does the firmware have more than one UI (for example a toy, and the full firmware behind a combo)? Map each
    one (`modes:` in the setup file).

Also tell the owner, before the port:

- what the SMK cannot keep: there is no TRS MIDI IN (PH8 is a matrix row), so MIDI clock in over TRS is gone;
- that the first boot of the port clears the stock firmware's settings area (untagged data, see step 3); the
  calibration and the way back to stock are not touched.

Filled examples: [examples/sloop.yaml](examples/sloop.yaml) (SLOOP),
[examples/rainbow.yaml](examples/rainbow.yaml) (Felucca 1.1.5 fork, a toy with a second UI),
[examples/ghoulbox.yaml](examples/ghoulbox.yaml) (Felucca 1.4.1 fork, own key path and power-on combos).

## 1. Baseline and base

```sh
git clone -c core.autocrlf=false "$FW" && cd <repo>
git config --local core.autocrlf            # must print false (else: git config core.autocrlf false, re-checkout)
sh build.sh
sha256sum build/<app>.bin build/<app>.fwsc build/loader/ota.bin > ../fm1-reference.sha256
sh tests/run_tests.sh || true               # record failures that exist before the port
```

The names differ per fork (`felucca.bin` / `felucca.fwsc` in Felucca and its forks, `x0x.*`, `omni.*`): check
`ls build/*.fwsc`. The app binary, the package and the loader must match later; other files in `build/` are
intermediates. Write
down the pre-existing test failures (big suites: `grep -n "FAIL\|OVER BUDGET"` the log) and the toolchain
versions. Builds embed `__DATE__`, and the JieLi clang ignores `SOURCE_DATE_EPOCH`: compare hashes on the same
day, or rebuild the baseline from the base commit on the day of the comparison (step 5).

Find the base:

```sh
git remote add sloop https://github.com/isod89/sloop-fm1.git
git remote add felucca https://github.com/hugelton/Felucca.git
git fetch sloop && git fetch felucca
git merge-base HEAD sloop/main      # found and recent: a SLOOP fork
git merge-base HEAD felucca/main    # otherwise: a Felucca fork
```

No common history (a copied tree): compare `firmware/hal/` and `tools/build.py` with the closest release.

## 2. Apply the board layer, area by area

```sh
git switch -c smk37
# SLOOP fork
git remote add ref https://github.com/genkigenki/sloop-fm1.git && git fetch ref smk37
git cherry-pick -x 8fad1a1..ref/smk37     # all commits on SLOOP 2.6
# Felucca fork
git remote add ref https://github.com/genkigenki/Felucca.git && git fetch ref smk37
git cherry-pick -x 1727537..ref/smk37     # ALL commits on Felucca 1.6, not just the tip
```

Resolve conflicts with the area table in [docs/03-porting-steps.md](docs/03-porting-steps.md), section 4. A
file the fork deleted: keep it deleted and move the SMK hunks to the fork's replacement. A Felucca fork older
than 1.6: see docs/03, section 2, and the branches `rainbow-smk37` / `ghoulbox-smk37`. Replace the layer's
`felucca-smk37` package stem and `FELUCCA` family defaults with the project's own (build.py, build.sh,
BUILDING.md, run_tests.sh, `tests/smk_owner_test.c`). In `fm1_flash_map.h` the FM-1 half takes the values of the
fork's own `fm1_flash.h`, never the layer's (the layer's carries 1.4.1's `FL_VBANK`). After each area:

- `sh build.sh && sha256sum -c ../fm1-reference.sha256` passes.
- `BOARD=smk37 sh build.sh` builds a package with the identity `SMK-37 Pro_9xx`.
- The tests show no new failures (run them after an FM-1 build, see step 5).
- `grep -n "BOARD_SMK37" firmware/src/*.c` shows only the expected places.

Stop and report to the owner after the system part (board switch, flash map, update path) and after the board
part (input, LCD, pad LEDs).

## 3. Storage

List every stored object by its enum (`OBJ_*`), not only by address, with its FM-1 sectors:

```sh
grep -n "OBJ_" firmware/src/storage.c | head -40
grep -rnE "0x[0-9A-Fa-f]{5}u?" firmware/src/storage.c firmware/src/eng_sample.c firmware/hal/fm1_flash*.h
```

| FM-1 address | On the SMK |
|---|---|
| `0x97000-0xDFFFF` (store) | move into the store window `0x9D000-0xBAFFF` |
| `0xE0000-0xE7FFF` (autosave and friends) | move into the store window |
| `0xFC000-0xFEFFF` (settings) | **inside the SMK's protected USR area: must move** into the store window |
| samples | `0xC2000-0xE9FFF` |

- Objects that share an A/B sector pair (told apart by a record type) keep sharing it, or each gets its own pair.
- The layer's layout ends at `0xAEFFF`, the owner tag sits at `0xAF000`; a fork's extra objects go into
  `0xB1000-0xBAFFF`.
- Expect the layer's `_Static_assert(OBJ_COUNT == ...)` to stop the build for a new object: give it a place in the
  layout, then extend the assert and the flash-map test.
- Data family: set it in `tools/build.py` (`SMK_DATA_FAMILY`, or `FELUCCA_DATA_FAMILY` in the environment) as the
  owner decided, and use the same family in the owner-tag test (`tests/smk_owner_test.c` may hard-code
  `FELUCCA`). A family has 1..7 characters (`GHOULBOX` became `GHOULBX`). The tag is 16 bytes with no NUL when
  the family has 7 letters: compare 16 bytes, not `sizeof`.
  With another family, add a case that a FELUCCA store is cleared. With `FELUCCA_DATA_UNTAGGED_OK 0` the first
  boot clears untagged data (the stock settings).

Check: the SMK flash-map test passes and covers every object.

## 4. Mapping

Implement `smk37-port.yaml`, using [docs/06-mapping-patterns.md](docs/06-mapping-patterns.md). Default order:

1. Middle 27 keys (keybed 5..31) = the FM-1 note keys, with velocity from the unit's factory curves.
2. Keep the firmware's own layout first: its knob order, its button grouping (by row or by printed name) and its
   button names. Then the extras.
3. The 16 pads as decided (default: the FM-1's 16 white keys; top row = hardware pads 0..7). Convert pad numbers in
   one place, for hits and LEDs alike.
4. Pad LEDs show what the FM-1 key LEDs showed, in the screen's colours.
5. K1 is the virtual MASTER pot; one encoder step per detent.
6. The extras: outer keys, faders (soft takeover), wheels (self-calibrating). No control repeats another's job
   unless the owner asked for it.
7. The screen rules: the screen shows what you touch first, same colours and places as the panel, no hidden modes.

Before mapping, read the fork's own input and LED code:

- **Every mode that owns the frame.** A fork may run its own loop instead of `ui_input()` / `ui_leds()` /
  `ui_draw()` (a toy mode). The layer's SMK extras do nothing there. Grep every reader of `fm1_in`,
  `panel_enc` and `fm1_input_edges` and every writer of `fm1_led*`, and wire the extras into each.
- **Code sized for the FM-1.** Grep for `14u`, `27u`, `FM1_NCOL` arrays and `14u + k` LED ids. A loop over 14
  button ids misses FX, SEQ, PLAY and REC (ids 14..17 on the SMK, `FM1_NBTN` is 18); an LED buffer of
  `FM1_NCOL` overflows (SMK LED ids go up to 63). Such LED code needs an SMK version (button LEDs and pads).
- **The fork's own power-on combos and flash checks.** The layer's `FM1_OCT_BOTH` / `FL_JEDEC_OK` cover only
  Felucca's places. Grep for `buttons & 3u`, `& 1u) ==` and `0x856014` (GHOULBOX's USB RESCUE in `bootguard.h`,
  its JEDEC check) and fix each (OCTAVE- is button 4 on the SMK).
- **Fields and timing the SMK input lacks.** A fork may read `fm1_in` fields `smk_input.h` does not have
  (GHOULBOX's crank reads `enc_dfr`): add them there. Grep for frame-based timing: the FM-1 scans 909 frames/s,
  the SMK 625.
- **The fork's own key path.** If the fork refactored `key_on` (GHOULBOX's `key_on_to(t, note, chord, chn)`),
  pass the velocity in from the caller instead of the layer's `key_vel(k)` inside `key_on(k)`. Route the outer
  keys through the same key_on / key_off helpers (own chord buffers, 10 slots), not straight to input_on /
  input_off, so chords, latches and splits work on them too; features that list held keys need them as well.

If the fork stores a button map, give the SMK its own magic number. Write the controls table in `SMK37.md` at the
top level as you go. Host UI tests: run the fork's tests for the FM-1; most forks have no SMK UI test, so say which
mapping parts are untested until the device loop.

## 5. Build both

Both boards write the same intermediate files, so the order matters:

```sh
BOARD=smk37 sh build.sh && cp build/<project>-smk37.fwsc ..   # and MODEL=elite, MODEL=mke
sh build.sh && sha256sum -c ../fm1-reference.sha256     # FM-1 last, so the tests see FM-1 binaries
sh tests/run_tests.sh                                   # no new failures compared with step 1
```

If the firmware has other builds (a browser emulator in `web/emu/`, a simulator, CI workflows), build and run them too:
they often compile `firmware/src/` without `hal/`, so a new macro the shared sources use must be defined there as well.
Run `web/emu/build.sh` with `sh` (not executable in a fresh clone). The web tests need node inside WSL (emsdk's:
`. ~/emsdk/emsdk_env.sh`); Windows node fails on drive-letter paths.
A CI workflow that publishes packages gets the SMK packages only if the owner says so.

A comparison on another day: `git worktree add ../fm1-base <base>`, build there, and compare with that.

Keep SMK code in board files and `#if BOARD_SMK37` blocks. See [docs/07-develop-for-both.md](docs/07-develop-for-both.md).

## 6. Device loop with the owner

The owner installs; the agent reads what the owner reports. Repeat until it plays well:

1. Hand over the package path, its SHA-256 and what changed. The owner installs with the fork's installer
   (Python or web), after the backup.
2. The owner turns on USB SERIAL (in the firmware's menu), restarts, and opens the console. Ask for `status`,
   `smk`, `padtest`, `leds` and the log lines around a problem.
3. Work through the bring-up table in [docs/03-porting-steps.md](docs/03-porting-steps.md), section 7: keys,
   pads (which row is which), faders, wheels, saving and reloading.
4. The owner plays and reports. Fix, rebuild both boards (step 5 order), re-run the tests, hand over again.
5. Confirm with the owner that flash `0xC1224` still reads `trimdat`.

## 7. Per-model builds

Every port builds one package per model, from the start:

```sh
BOARD=smk37 MODEL=pro   sh build.sh   # <project>-smk37.fwsc: SMK-37 Pro, also for Starrykey 37 Play
BOARD=smk37 MODEL=elite sh build.sh   # <project>-smk37-elite.fwsc
BOARD=smk37 MODEL=mke   sh build.sh   # <project>-smk37-mke.fwsc
```

Both layers (SLOOP 2.6, Felucca 1.6) carry the "SMK-37 Elite and MKE-P37 builds" commit (`SMK_MODEL`: identity,
loader name, recovery identity, update record name, installer filters). On an older fork, take that commit from
the layer or a worked example branch, and replace the example's project names (package stem, data family) in
build.py, build.sh, BUILDING.md, run_tests.sh and `tests/smk_owner_test.c`. Each package reports its model's
name, so the stock updater can restore that model's factory firmware. The installer's port-name filters must
include this firmware's USB name. Parse identities to the first NUL.

## 8. Deliver

- **Upstream pull request** (see "The goal" above): commits behind `BOARD_SMK37`, the project's own name and
  look, `SMK37.md` and the one README line. The PR text says what it adds, that the FM-1 build is unchanged
  (byte-identical), which tests ran and, honestly, what was tested on a unit, and that the porter hopes it gets
  taken in. Offering to help maintain the target is up to the porter (offer it only if you can). Sources only:
  leave generated and published directories (the site in `docs/`, built installer copies) to the maintainer's
  build.
- **Until merged:** the branch and a release with the `.fwsc` per model in the porter's fork of the original
  (GPL-3.0). Never attach stock files or dumps. Archive the fork once the PR is merged.
- **Installer:** before delivering, check the resume path (hard rule 9): an SMK loader never gets an FM-1
  package, an FM-1 loader never an SMK one, and a resume without the package's identity writes nothing. Older
  Felucca forks (1.1.5) have the hole: `resume()` matches `id.model === "ota-" + model` and, without a product,
  takes any loader. Reference: the SLOOP layer's `web/fm1ota.js` (genkigenki/sloop-fm1 `smk37`, also on the
  `ghoulbox-smk37` branch): `resume(image, onStep, {package, product, anyModel})`, `sameKeyboard`, nothing written
  without the identity, and its tests; the web test's fake device needs a settable identity after the write
  (Elite loader, Pro package). The Felucca 1.6 layer keeps `resume(image, onStep, product)` with the same check.
  If the fork changed `resume()` itself (GHOULBOX added a 4th argument `waitMs` and a reload path), take the
  reference file, re-add the fork's parts as options (`opts.waitMs`) and convert every caller and test.
- Commit messages describe the change. The owner merges, pushes and publishes.

## Done when

- [ ] `smk37-port.yaml` filled and approved by the owner
- [ ] FM-1 build byte-identical to the baseline
- [ ] SMK build passes the host tests (no new failures; FM-1 built last)
- [ ] The flash allow-list and its asserts are unchanged or stricter; no object in a protected range
- [ ] The device checklist passes on a real unit (owner confirmed)
- [ ] One package per supported model, each with its model's identity
- [ ] Every installer path (install and resume) checks the model against the package, with tests
- [ ] An upstream PR touches no generated or published directory
- [ ] The project's own name, logo and boot on the SMK; packages `<project>-smk37[-elite|-mke].fwsc`
- [ ] `SMK37.md` (models, controls, build, install, the way back, safety) and the one README line
