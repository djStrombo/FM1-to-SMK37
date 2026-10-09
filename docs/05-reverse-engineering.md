# 05: How the facts were obtained

Everything in [01-hardware.md](01-hardware.md) was found in two ways. First by reading the stock SMK-37 Pro
firmware with public tools and comparing it with the FM-1 and its well-documented open firmwares. Then by
checking the results on a real unit with a custom firmware. This page describes the method, so that anyone can
repeat it or extend it to a future stock version. It contains no vendor code. Get the stock files yourself from
M-Vave.

## 1. Tools

| Tool | Use |
|---|---|
| [jl-misctools](https://github.com/kagaimiq/jl-misctools) (kagaimiq) | unpack the `.fwsc` package into its parts |
| JieLi pi32v2 toolchain (the one the firmware builds use) | `objdump` with exact pi32v2 decoding |
| [Ghidra](https://ghidra-sre.org/) with [ghidra-jieli](https://github.com/kagaimiq/ghidra-jieli) | navigation, cross references, decompiler view |
| [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool) (kagaimiq) | read the flash id and dump the flash over the mask-ROM bootloader |
| JieLi AC79 SDK headers (`fw-AC79_AIoT_SDK`) | SFR names, SPI pin groups (`include_lib/driver/cpu/wl82/asm/spi.h`) |
| [FM-1-RE](https://github.com/AL-255/FM-1-RE), Felucca and SLOOP sources | the FM-1 side: what each SFR and helper does, already named |
| [jielie](https://github.com/kagaimiq/jielie) | chip families, boot process, USB_KEY |

## 2. Unpack the stock package

Use the "new firmware" unpacker from jl-misctools (`firmware/fwunpack_newfw.py`; see the tool's help for its
arguments). The parts you need are:

- `app.bin`: the application, the main subject,
- `cfg_tool.bin` and `cfg`: configuration and resources,
- `uboot.boot`: the second-stage bootloader,
- `isd_config.ini`: the boot configuration,
- `ota.bin`: the update loader,
- `flash.bin`: the encrypted image as it lies in flash.

**Note:** the stock v016 package uses 36 interleave blocks instead of 20
([02-update-and-recovery.md](02-update-and-recovery.md), section 2.2). If an unpacker assumes 20, every CRC fails.
Older versions (v011) use 20.

Quick comparisons that already tell a lot:

- `cmp` the SPL, `isd_config.ini` and `ota.bin` of the SMK package with the FM-1's. They are identical, so the boot
  chain and the update mechanism are shared.
- Compare the first 16 KiB of both `flash.bin` files. They are identical too.
- Read the region table (decrypted flash, from offset 0x4060). It gives the SMK flash map. The entries for VM, BTIF,
  USRTRIM, USRFLASH and USR are **absolute** flash offsets. Do not add 0x4000.

## 3. Load the app at the right address

`app.bin` executes in place at **0x02000120**, not 0x02000000. To confirm this for any version, look for a table
of pointers to strings (for example the note-length names) and check at which base they land exactly on string
starts. Also check that function pointers in data land on function prologues. If you analyse at 0x02000000,
subtract 0x120 from every absolute flash pointer you meet in the code.

To disassemble with the JieLi toolchain's `objdump`, wrap the raw image in a minimal ELF:

- ELF32, little-endian, `e_machine` = 241 (pi32v2),
- one `PT_LOAD` segment: file contents at virtual address 0x02000120, flags R+X,
- optionally empty segments for RAM (0x01C00000, 512 KiB) and the SFR space (0x00010000..0x00060000), so that
  references resolve in Ghidra.

A short script with Python's `struct` module does this. Then:

```sh
~/.jieli/toolchain/common/bin/objdump -d app.elf > app.dis
```

Load the same ELF into Ghidra with the ghidra-jieli module for cross references.

**Decoder pitfalls.** The Ghidra module mis-decodes a few pi32v2 instructions. Check with `objdump` whenever an
offset or a register matters:

- byte loads and stores with a register plus displacement: the displacement is split across two nibbles, and the
  decompiler can show it 16 times too large (`+0x10d` where the real offset is `+0x1d`). The data register of a
  byte store can also be wrong.
- a few logical operations and FPU instructions show up as garbage or wrong mnemonics. The pad velocity math in
  the stock firmware is FPU code and could only be read in part.
- string annotations in the decompiler output can point at the wrong string. Resolve the pointer yourself.

## 4. Find each subsystem

Search the disassembly for **SFR addresses** as immediates. Each peripheral leads to its driver, and the driver
leads to the tables.

| Look for | Peripheral | Leads to |
|---|---|---|
| `0x11E00` | SPI2 | the key-matrix shift (CON, BAUD, DMA address, DMA count), its interrupt handler, the scan order, the latch pin |
| `0x11D00` | SPI1 | the LCD driver (init table, window and fill routines) and the pad LED frame |
| `0x51020` | `IOMAP_CON1` | which SPI pin group each bus uses. Compare the bits with `spi.h` in the AC79 SDK. |
| `0x13100`, `0x13104` | SARADC | channel numbers, CON value (timing), the interrupt handler with the mux state machine |
| `0x50000 + port * 0x40` | GPIO ports | pin direction, pulls, input reads (the matrix return lines), outputs (D/C, CS, latch) |
| `0x16A0C` | USB PHY pad control | the two button-LED commons |
| `0x12100` | UART1 | MIDI OUT setup and its pin |

The GPIO helpers are small functions called with a pin id and a value. Name them once, using the FM-1 firmware
where they are already known: output level, direction, input enable, pull-up, pull-down. Then every pin set-up
call becomes readable.

Tables found from the code that reads them:

- **key contact table**: 37 pairs of matrix codes, read by the per-frame key loop,
- **button table**: 18 matrix codes, read by the button timer callback,
- **encoder table**: 8 pairs of codes, read by the quadrature decoder,
- **LED table**: 19 entries of group and bit, read by the LED multiplex code,
- **pad map**: 16 bytes, mux phase to pad index, read by the ADC handler,
- **LED chain map**: pad to position in the WS2812 chain, read by the colour setter,
- **calibration record**: found from the file name string `usrtrim` and the marker `trimdat`.

Strings also help. The USB string descriptors are stored as UTF-16 ("SMK-37 Pro Midi"). The calibration UI text
("Scroll PITCH to bottom") names the wheels and their order. The identity record `SMK-37 Pro_016` sits next to
the update code.

## 5. Things the stock code cannot tell you

Static reading gives pins, registers and algorithms. Some facts can only be settled on the device:

| Question | How it was settled |
|---|---|
| Flash part | `jl-uboot-tool` prints the JEDEC id when it connects in UBOOT (0xEB6014 on the tested unit) |
| Physical pad order (which mux is the top row) | the debug console's raw pad readings while pressing each pad |
| Button names for ids 6..17 | the console's button bit mask while pressing each button |
| Encoder order and direction | the console's per-encoder step counters |
| LED colour order | a test pattern with pure red, green and blue on known pads |
| Wheel and fader ranges | raw readings at rest and at both ends |
| ADC timing | the console's counters of finished and missed conversions. With the FM-1 timing almost all conversions were missed. |
| Update path | installing a custom package from the stock app, then sending the soft key to reach UBOOT |

A debug console is the most useful single tool for this. Felucca-family firmware has one over USB serial. Add a
command that prints the raw inputs early in the port.

## 6. Ground rules

- Keep notes with a confidence level for each fact: read from the code with concrete constants, inferred, or
  guessed. Hardware tests turn inferences into facts.
- Publish facts in your own words and tables. Do not publish vendor binaries, dumps, disassembly or decompiled
  code.
- Never test a flash write path on a unit without a verified full backup.
