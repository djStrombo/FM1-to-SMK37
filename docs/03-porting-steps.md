# 03: Porting a firmware, step by step

This walkthrough ports a Felucca-family FM-1 firmware to the SMK-37. The board layer comes in two forms:

- **SLOOP forks:** the patch series from [Snoop37](https://github.com/genkigenki/Snoop37), branch `smk37-board`,
  written against SLOOP 2.5.
- **Felucca forks:** one commit on Felucca main, branch `smk37` of
  [genkigenki/Felucca](https://github.com/genkigenki/Felucca) (the same as hugelton/Felucca#237).

Both touch the same files; file names below are SLOOP's, Felucca's are mostly the same.

**Ground rules for the port:**

- Put every change behind one compile-time switch (`BOARD_SMK37`, default 0). Then the FM-1 build stays
  **byte-identical**: compare the hashes of the app binary, the package and the loader before and after.
- Never relax the flash allow-list (section 4.3).
- Commit per area. Small commits make the next rebase on upstream easy.

## 0. Prerequisites

- A Linux machine or WSL2. The JieLi toolchain is distributed for Linux. On Windows, run every build and test in
  WSL, not in Git Bash (Git Bash mangles `$` in commands passed on to WSL; put longer commands in a script and run
  `wsl bash script.sh`). The firmware's `BUILDING.md` may be written for macOS; the steps below work on Linux.
- `git`, `sh`, a host C compiler, and Python 3 with **Pillow that has raqm** (`ImageFont.Layout`). Distribution
  packages are often too old (Ubuntu 22.04's 9.0.1 fails); use a virtual environment:

  ```sh
  python3 -m venv ~/.venv-fw && ~/.venv-fw/bin/pip install Pillow fonttools
  ~/.venv-fw/bin/python -c "from PIL import features; print(features.check('raqm'))"   # True
  ```
- The JieLi pi32v2 toolchain. SLOOP and Felucca ship `tools/get_toolchain.sh`, which downloads it from JieLi's
  package server into `~/.jieli/toolchain`.
- A few files from the JieLi AC79 SDK (`fw-AC79_AIoT_SDK`, tag `AC79NN_SDK_V1.2.1_2023-12-13`, folder
  `cpu/wl82/tools`). The firmware's `BUILDING.md` names them and their hashes. A sparse clone is enough:

  ```sh
  git clone --depth 1 --filter=blob:none --sparse \
      --branch AC79NN_SDK_V1.2.1_2023-12-13 https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK.git
  git -C fw-AC79_AIoT_SDK sparse-checkout set cpu/wl82/tools
  ```

- An SMK-37 with a **full flash backup** ([02-update-and-recovery.md](02-update-and-recovery.md),
  section 3).

Line endings: Git for Windows converts to CRLF by default, and patches and build scripts break. Clone with
`git clone -c core.autocrlf=false URL` (the option after `clone` is stored in the repository; `git -c ... clone`
is not), or run `git config core.autocrlf false` in the clone and check out again. Check:
`git config --local core.autocrlf` prints `false`.

Overrides if the tools are not in their default places: `JIELI_TOOLCHAIN` (default `~/.jieli/toolchain`) and
`AC79_SDK` (the SDK clone), as the firmware's `tools/build.py` reads them.

## 1. Get the firmware source and build it unchanged

```sh
git clone https://github.com/<author>/<firmware>.git
cd <firmware>
sh build.sh                       # FM-1 build
sha256sum build/*.bin build/*.fwsc build/loader/ota.bin > ../fm1-reference.sha256
```

The app binary, the package and the loader must match later; the other `.bin` files are intermediates. Builds
embed `__DATE__` (the JieLi clang ignores `SOURCE_DATE_EPOCH`), so compare on the same day, or rebuild the
baseline from the base commit on the day of the comparison: `git worktree add ../fm1-base <base>`.

Run the host tests if the project has them (`sh tests/run_tests.sh` in SLOOP). Note which tests already fail,
so you do not blame the port for them later.

Find out what the firmware is based on:

```sh
git remote add sloop https://github.com/isod89/sloop-fm1.git
git remote add felucca https://github.com/hugelton/Felucca.git
git fetch sloop && git fetch felucca
git merge-base HEAD sloop/main      # a SLOOP fork if this finds a recent commit
git merge-base HEAD felucca/main    # otherwise a Felucca fork
```

Many forks were started from a copy rather than a git fork. In that case, compare `firmware/hal/` and
`tools/build.py` by hand with the closest SLOOP or Felucca release.

## 2. Get the board layer

**Felucca fork:** fetch the branch and cherry-pick all its commits on Felucca 1.5.1 (`ef1f561`), then go on with section 4:

```sh
git remote add ref https://github.com/genkigenki/Felucca.git && git fetch ref smk37
git switch -c smk37 && git cherry-pick -x ef1f561..ref/smk37
```

Expect conflicts where the fork changed the build, the flash header, the UI input and the sequencer. A file the
fork deleted (modify/delete conflict): keep it deleted and carry the SMK hunks to the fork's replacement.

**SLOOP fork:** the patch series.

```sh
git remote add snoop37 https://github.com/genkigenki/Snoop37.git
git fetch snoop37
git log --oneline --reverse <base>..snoop37/smk37-board
```

`<base>` is the SLOOP release the branch starts from (its first commit message names it). Export the series:

```sh
git format-patch <base>..snoop37/smk37-board -o ../smk37-patches
```

The series, in order, covers roughly these steps:

1. **System:** board switch, identities, flash map and allow-list, update path, package layout, installer
   changes, tests.
2. **Board layer:** input HAL (`smk_input.h`), LCD pins and init, pad LEDs, first UI mapping.
3. **Flash part:** accept JEDEC 0xEB6014.
4. **Bring-up fixes from a real unit:** ADC timing, fader filter, pad rows, button names, console commands.
5. **Wheels:** pitch bend and mod-wheel vibrato.
6. **Controls:** one encoder step per detent, pad step display, outer keys, knob and fader layout, app slot size,
   pad colours, button LEDs.

The Snoop37 branding (boot intro, jingle, its own screens) lives on `main`, behind the build flag `SNOOP37`,
and is not part of the board series.

## 3. Apply it

On a new branch:

```sh
git switch -c smk37
git am -3 ../smk37-patches/*.patch
```

`-3` lets git fall back to a three-way merge, so most conflicts end up as normal conflict markers. Resolve them,
`git add` the files, and run `git am --continue`. If one patch is too far off, `git am --skip` it and redo it by
hand from the table below. Then continue with the rest.

Cherry-picking works too: `git cherry-pick <base>..snoop37/smk37-board`.

**For a fork without SLOOP or Felucca history** (a copied tree), take the Felucca commit as a model and apply
it file by file. New files (`smk_input.h`, `fm1_flash_map.h`, the SMK tests) go in unchanged. For the changed
files, read each hunk and apply its intent.

## 4. Resolve conflicts by area

| Area | Files (SLOOP names) | What the series does | Hints |
|---|---|---|---|
| Board switch | `firmware/hal/fm1_cc.h` | defines `BOARD_SMK37` (default 0) | applies cleanly everywhere |
| Build | `tools/build.py`, `build.sh`, `BUILDING.md` | `--board fm1\|smk37` (or `BOARD=` env); adds `-DBOARD_SMK37=1` to the app **and** the update loader; identity prefix `SMK-37 Pro_9`; output name; app slot `0x97400` written into a per-board copy of `app.ld` | Forks rename the package and the identity. Keep their names for the FM-1 and add the SMK entry next to them. The FM-1 path must not get any new compiler flag. |
| Package | `tools/fm1pkg_make.py` | per-board tables: PRCT size `0x9D000`, the SMK region table (VM, PRCT, BTIF, USRTRIM, USRFLASH, USR with stock flags), app slot | Take the SMK table as it is. Do not merge it with the FM-1's. |
| Input HAL | `firmware/hal/smk_input.h` (new), `fm1_input.h`, `felucca.c` includes | new HAL with the FM-1 API (`fm1_in`, `fm1_input_init`, `fm1_input_tick`, `fm1_input_scan`, `fm1_enc_take`, `fm1_input_edges`, `fm1_input_note_edges`, `fm1_led_key`) plus SMK extras: velocity, pads, faders, wheels, outer keys. `felucca.c` includes it instead of `fm1_input.h` and `fm1_adc.h`. | If the fork changed the FM-1 input API (renamed fields, added a shift layer), add the same names to `smk_input.h`. Do not change the scan order (see [01-hardware.md](01-hardware.md), 5.1). |
| ADC | `smk_input.h` | MASTER pot becomes a virtual pot on encoder K1; battery from mux C | Forks that read more FM-1 pots need more virtual pots. Keep the SMK ADC timing. |
| LCD and pad LEDs | `firmware/hal/fm1_lcd_hw.h`, `src/lcd.c` | pins PB6/PB7/PC8/PB5, SPI1 group A, no backlight, SMK init table; `fm1_padled_send` / `fm1_padled_done` switch SPI1 to group B for the LED frame | Forks that tuned the FM-1 init table: keep theirs under `#else`. The LED flush must run only between LCD transfers. |
| Flash | `firmware/hal/fm1_flash.h`, `fm1_flash_map.h` (new) | allow-list of writable ranges, `_Static_assert`s against the protected ranges, an independent guard in the RAM flash driver, `FL_JEDEC_OK` with 0xEB6014 | **Never weaken this.** If the fork stores more objects, give them space inside `0x9D000-0xBAFFF` and extend the asserts. |
| Storage | `src/storage.c`, `src/eng_sample.c`, `src/editor.c`, `src/project.c`, `src/console.c` | SMK sectors for every stored object (projects, preset, autosave, FM6 bank, settings) in `0x9D000-0xAEFFF`; two 80 KiB sample slots in `0xC2000-0xE9FFF`; slots 3 and 4 empty | The most fork-specific part. List every object by its enum (`OBJ_*`) with its FM-1 sectors; objects may share an A/B pair (told apart by a record type). FM-1 settings at `0xFC000`/`0xFD000` lie in the SMK's protected USR area and must move. Lay everything out in the store window, extras in `0xB1000-0xBAFFF`, and assert the end addresses. The Felucca layer's `_Static_assert(OBJ_COUNT == 10u)` stops the build for a new object, as intended. |
| Update | `src/ota.c`, `loader/loader.c`, `loader/ldr_core.c`, `src/felucca.c` | staging `0xBB000`, update record at `0xBFF00`; record name `ota-SMK-37 Pro_016`; loader name `ota-SMK-37 Pro_900`; loader writes only the app area and VM; identities `SMK-37 Pro_900` / `SMK-37 Pro_000` | Felucca forks with their own loader name: keep the `ota-` prefix and the model text exactly. |
| MIDI | `src/felucca.c` | TRS MIDI IN forced off on the SMK, with a build error if it is switched on | PH8 is a matrix row on the SMK. Keep the guard. |
| UI | `src/main.c`, `src/panel.c`, `src/ui_input.c`, `src/seq.c`, `src/voice.c`, `src/bootguard.h` | button and knob defaults, pads as white keys, outer keys, faders, wheels, LED rules, power-on combos on the SMK's OCTAVE buttons | Expect most conflicts here. See section 5. |
| Console | `src/console.c` | debug commands `smk`, `padtest`, `leds` | |
| Host tools | `tools/fm1_install.py`, `web/fm1pkg.js`, `web/fm1ota.js`, web installer page | SMK port names, SMK identities, 20- or 36-block packages checked by CRC, the stock SMK package accepted for the return to stock | Forks often have their own web installer. Port the block detection and the port-name filter into it. Once it accepts SMK loaders, `resume()` must check the loader's model against the package (as `install()` does) and write nothing without the package identity; add a test. In an upstream PR, change `web/` only, never the built copy in `docs/`. |
| Tests | `tests/*` | SMK flash-map test, package layout test, SMK variants of the update and loader tests | Run them. The loader test checks that the protected ranges stay untouched. |

After this step, check two things:

```sh
sh build.sh && sha256sum -c ../fm1-reference.sha256      # the FM-1 build is unchanged
BOARD=smk37 sh build.sh                                   # the SMK build compiles and links
```

## 5. Map the UI

The FM-1 has 27 note keys, 14 buttons, 7 encoders and a MASTER pot. The SMK-37 has far more. The series maps
it like this. Full tables are in [04-controls-mapping.md](04-controls-mapping.md).

| SMK-37 | Becomes | How |
|---|---|---|
| keys 5..31 (F3..G5, the middle 27) | the FM-1's 27 note keys, with velocity | `smk_input.h` sets note bits 0..26 from keybed keys 5..31 |
| keys 0..4 and 32..36 (C3..E3, G#5..C6) | extra notes on synth tracks, extra drum sounds on the drum track | a separate event queue (`smk_extkey_take`), handled in the UI |
| 16 pads | the 16 **white** keys of the 27 (F3 G3 A3 B3 C4 D4 E4 F4 / G4 A4 B4 C5 D5 E5 F5 G5) | top row (hardware pads 0..7) = white keys 1..8 in a step grid; as a keyboard, low notes at the bottom (pads 8..15). Convert in one place (`SMK_PAD_OF_WHITE`); the pad sets the same note bit as the key |
| pad LEDs | what the FM-1 key LEDs showed: steps, playhead, layer tiles, in the track colour | drawn from the UI state once per frame |
| piano layout on the pads (optional) | for scale or key pages | bottom row C4..C5 white, top row the black keys between them |
| K1..K8 | K1 MASTER (virtual pot), K2 SELECT, K3 ALGORITHM, K4 PRESETS, K5..K8 KNOB 1..4 | SLOOP's panel table (function to hardware id) |
| 18 buttons | FM-1 functions by printed name, 4 left free | SLOOP's panel table. The hardware calibration combo re-teaches it. |
| faders 1..4 | per-track level, filter, reverb send, delay send (FADER BANK switches) | a fader only takes over once it is moved |
| pitch wheel, mod wheel | pitch bend of the selected synth track, vibrato | self-calibrating, see [01-hardware.md](01-hardware.md), 6.5 |

Hints for other firmwares:

- **Start from the FM-1 behaviour.** Map the 27 middle keys, the pads as white keys, and the FM-1's buttons and
  knobs. Then the fork's manual applies on the SMK as it is. Use the extra controls only after that.
- If the fork reads FM-1 note keys by key id (14..40 on the FM-1), translate in one place. Do not spread
  `BOARD_SMK37` through the UI code.
- A pad press must end the note it started, even when the layout changed while it was held. The reference HAL
  stores the note per pad for this reason.
- The FM-1 power-on combos use OCT- and OCT+. They map to OCTAVE- and OCTAVE+ (button ids 4 and 5).
- Firmwares with a stored button map (SLOOP's panel table) need a new magic number for the SMK, so that an FM-1
  map is never loaded on the SMK.

## 6. Build

```sh
BOARD=smk37 sh build.sh && cp build/<app>.fwsc ../        # keep the SMK package
sh build.sh && sha256sum -c ../fm1-reference.sha256       # FM-1 last: both boards share build/ intermediates
sh tests/run_tests.sh                                     # the tests expect FM-1 binaries
```

The reference build writes `build/sloop-smk37.fwsc` (identity `SMK-37 Pro_900`). Check:

- the app fits the `0x97400` slot (the linker fails otherwise),
- the package identity is `SMK-37 Pro_9xx`,
- the host tests show no new failures (the SMK tests: flash map, owner tag, package, update, loader). Most forks
  have no UI test for the SMK mapping; that part is checked on the device.

## 7. Test on the device

1. Make the full flash backup if you have not done so yet.
2. Install the SMK package ([02-update-and-recovery.md](02-update-and-recovery.md), section 4).
3. Turn on the USB serial console. In SLOOP-based firmware: hold the HOME button (PATCH on the SMK), go to
   AUDIO, set USB SERIAL to ON, then restart. A build with `FELUCCA_CDC_ON=1` has the console on from the start.
   Open the serial port at any baud rate.
4. Work through the bring-up checklist:

| Check | Console / action | Expected |
|---|---|---|
| ADC runs | `smk`: `adc_ok` rises, `adc_miss` stays near 0 | if `adc_miss` rises, the ADC timing is wrong |
| Pads | `smk`: `pad raw` and `pad base` per pad | idle near the baseline, a hit well above it; the top row is pads 0..7 |
| Pad LED colours and order | `padtest` | hardware pads 8..11 light red, green, blue, white (for 20 s): the first four of the **bottom** row (some console texts say "top row"; trust the unit) |
| Pad LED state | `leds` | the colour word the firmware holds for each pad |
| Faders | `smk`: `fader raw` and `fader` | raw 0..1023, value 0..127, both ends reachable |
| Wheels | `smk`: `wheel0`, `wheel1`, `bend`, `modw` | pitch rests around 535, mod moves the other way (up = lower raw) |
| Buttons | `smk`: `buttons` bit mask | one bit per button, ids as in [01-hardware.md](01-hardware.md), 5.3 |
| Encoders | `smk`: `enc0..enc7` | one step per detent, K1..K8 in order |
| Keys | play all 37 keys softly and hard | notes from C3 to C6, velocity follows the stroke |
| Flash | `flr` (read a flash window), save a project, power-cycle | the project survives; `0xC1224` still reads `trimdat` |
| Audio, USB MIDI, USB audio | play | as on the FM-1 |

5. When something is wrong, compare with the reference implementation before changing hardware constants. Most
   bring-up bugs were in timing (ADC) and filtering (faders), not in the pin maps.

## 8. Release and roll back

- Tag a release and build with the release version. The identity becomes `SMK-37 Pro_9XY`.
- Ship only your firmware package and your source, under GPL-3.0 like the code it comes from. Never ship stock
  firmware files or flash dumps.
- An upstream pull request carries sources only. The maintainer builds and publishes the site (`docs/`); SMK docs
  go at the top level (`SMK37.md`) or another unpublished place.
- To go back to stock: [02-update-and-recovery.md](02-update-and-recovery.md), section 6.
