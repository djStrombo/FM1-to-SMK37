# 07: Develop for both boards

A port is easy to keep alive when one source tree builds the FM-1 and the SMK-37 Pro, and new features land on
both. This is how the ports were kept that way. Use it for a new firmware too: write it for the SMK, keep the
FM-1 working.

## 1. Board code stays in board files

- The SMK input HAL, LCD, pad LEDs and flash map live in their own files (`smk_input.h`, the board's flash map,
  the per-board linker length). Shared files include them under `#if BOARD_SMK37`.
- In shared UI and engine code, `#if BOARD_SMK37` blocks are short and few: identities, the UI mapping, the
  storage layout, the console. `grep -n BOARD_SMK37` should read like a list of the port's decisions.
- With `BOARD_SMK37` 0, the FM-1 outputs are byte-identical to the upstream build. That is the test that the
  port changed nothing for FM-1 users, and the reason an upstream maintainer can merge it.

## 2. Features against a small capability layer

Write features against what a board **has**, not against which board it is. A few constants and calls are
enough:

```c
/* board_caps.h: one place that says what the panel has (values for the SMK-37 Pro / the FM-1) */
#if BOARD_SMK37
#define CAP_KEYS        37    /* velocity keys; the FM-1 range is keys 5..31 */
#define CAP_PADS        16    /* RGB pads; hardware 0..7 top row, 8..15 bottom */
#define CAP_FADERS       4
#define CAP_WHEELS       2
#define CAP_OUTER_KEYS  10
#define CAP_RGB          1
#else
#define CAP_KEYS        27
#define CAP_PADS         0
#define CAP_FADERS       0
#define CAP_WHEELS       0
#define CAP_OUTER_KEYS   0
#define CAP_RGB          0
#endif

void caps_pad_led(int pad, uint32_t rgb);   /* SMK: the pad; FM-1: the white key's LED (or nothing) */
int  caps_fader(int i);                     /* 0..1023 after soft takeover; -1 when not moved yet */
int  caps_wheel(int i);                     /* calibrated -512..511 around the centre */
```

Then each feature has an FM-1 fallback in the same place:

| Feature | SMK-37 Pro | FM-1 fallback |
|---|---|---|
| Step grid | 16 pads in track colours | the white keys' LEDs, as before |
| Sound picker | pads + screen | the screen list, scrolled with PRESETS |
| Fader banks | 4 faders | a menu page with four dials |
| Wheels | bend, vibrato or a macro | a menu value, or off |
| Outer-key drums | 10 keys | not available (the feature hides itself) |

With `CAP_*` zero the compiler removes the SMK paths, which keeps the FM-1 build identical.

## 3. Build and test matrix

Build and test every change on both boards, locally and in CI, in this order (both boards write the same
`build/` intermediates, and the tests expect FM-1 binaries; copy each package out before the next build):

| Job | Command | Check |
|---|---|---|
| SMK-37 Pro | `BOARD=smk37 sh build.sh` | builds; package identity `SMK-37 Pro_9xx` |
| SMK models | `BOARD=smk37 MODEL=elite sh build.sh`, `MODEL=mke` | identities `SMK-37 Elite_…`, `MKE-P37_…` (layers with `SMK_MODEL` only; the Felucca layer builds the Pro) |
| FM-1 | `sh build.sh` | hashes equal the upstream baseline (`sha256sum -c`) |
| Host tests | `sh tests/run_tests.sh` | no new failures; flash map, loader, OTA, owner tag, storage |
| Screens | the host screen renderer | one image per control, compared with the docs |

A CI workflow only needs the JieLi toolchain (cached) and the matrix above. Host tests on glibc need
`CC='cc -D_DEFAULT_SOURCE'` (see [08-pitfalls.md](08-pitfalls.md)).
