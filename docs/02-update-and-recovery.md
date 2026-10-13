# 02: Update, backup, recovery and return to stock

The SMK-37 and the FM-1 share the update machinery: the same update library in the app, the same update
loader (`ota.bin`, byte-identical), the same second-stage bootloader and the same mask-ROM bootloader. Everything
Felucca and SLOOP do on the FM-1 works on the SMK-37 once a handful of names and sizes are adjusted.

## 1. How an update runs

1. **Check (stock or custom app running).** The host sends the enter-upgrade command over USB MIDI. The running
   app pulls the package from the host in small reads and checks it. If the package is accepted, the app copies
   the package's update loader into a staging area in flash and writes an **update record**. The record holds
   the loader's address and a name such as `ota-SMK-37 Pro_016`. The app then resets.
2. **Write (update loader running).** The second-stage bootloader finds the record and starts the loader. The
   loader enumerates on USB under the name from the record. It pulls the package again and writes the app area.
   When it is done it removes its records and resets.
3. **Run.** The new app starts.

If power fails during step 2, the record is still there and the loader starts again at the next power-on. Run
the installer again and it resumes.

**Verified on the tested unit:** the stock SMK-37 Pro app (v016) accepts a SLOOP-style package built for the SMK
and starts the custom update loader from it.

## 2. Protocol facts

All messages are SysEx over USB MIDI. Framed messages look like this:

```
F0  pack7( 00 59  cmd  len(3 bytes, LE)  body  checksum )  F7
```

- `pack7` packs 8-bit bytes into 7-bit MIDI data, least significant bits first.
- The checksum is the inverted 8-bit sum of the body.

| Message | Bytes (on the wire) | Notes |
|---|---|---|
| Identity query | `F0 00 32 45 00 00 00 40 7F F7` | Reply: cmd `0x11`, 27-byte zero-padded identity text |
| Enter upgrade | `F0 22 24 35 7F F7` | Same command on FM-1 and SMK-37 |
| Read request (device to host) | cmd `0x30`: flags, address (4 bytes), length (3 bytes) | The device pulls the package. The host answers with cmd `0x30` carrying the same address and the data. |
| Handshake | the device reads 8 bytes at `0xE0000000` (check step) and `0xF0000000` (write step) | The host answers `success\0` |
| UBOOT soft key | `F0 22 24 35 7D F7` | Understood by the Felucca/SLOOP update loader and app, **not** by the stock app. Restarts the chip into the mask-ROM bootloader. |

The stock app resets after the check step even when the handshake fails. The SLOOP loader is stricter.

### 2.1 Identities

| Who answers | Identity text | Notes |
|---|---|---|
| Stock app | `SMK-37 Pro_016` | `FM-1_015` on the FM-1 |
| Stock update loader | `ota-SMK-37 Pro_016` | taken from the update record |
| Custom app (reference port) | `SMK-37 Pro_900`, release builds `SMK-37 Pro_9XY` | |
| Custom update loader | `ota-SMK-37 Pro_900` | |
| Custom recovery screen | `SMK-37 Pro_000` | |

Hosts compare models by the text before the underscore (`SMK-37 Pro`). The usual pattern `([^_]+)_(\d+)` accepts
the space. Installers must also accept MIDI port names that contain `SMK`. The stock port is called
"SMK-37 Pro ..." and an FM-1 port filter refuses it.

**The update record name.** When a custom app hands over to a loader, it writes the record itself. On the SMK it
must write `ota-SMK-37 Pro_016` (18 bytes, zero-filled up to offset +0x27 of the record), not `ota-FM-1_015`.
The loader is identical on both devices and reads its USB name from this record. With the wrong name, M-Vave's
tool may not recognise the official loader during a return to stock.

### 2.2 The `.fwsc` package container

A package is a JieLi "UFW" image (header, `flash.bin`, `ota.bin`, resources) with the identity woven in:

- The start of the file is split into **blocks of 0x30 bytes**. Bytes 0x00..0x2E of each block are payload.
  Byte 0x2F is a marker.
- For block `i`, the marker is `identity[i] + i + 1` (mod 256) while there are identity characters left, and
  `0x7D` after that.
- The image the device reads during an update is the file with all marker bytes removed.

| Package | Blocks |
|---|---|
| FM-1 stock, Felucca, SLOOP | 20 |
| **SMK-37 Pro stock v016** | **36** (14 identity characters + 22 x `0x7D`) |
| SMK-37 Pro stock v011 | 20 |

An installer that assumes 20 blocks reads a v016 package 16 bytes out of place, and every CRC fails. A robust
rule: count blocks while `i < 20` or the marker is `0x7D`. Then check the CRCs of `flash.bin` and `ota.bin`
inside the result. If they fail, fall back to 20 blocks.

**Quirk.** In stock packages, the stored CRCs of the smaller resource files (USR, `isd_config.ini`,
`script.ver`, `blimit.bin`) do not match the bytes served. Only `flash.bin` and `ota.bin` match. An installer
that checks every file rejects every stock package. Check only those two.

### 2.3 What the package writes

A package for the SMK must carry the SMK's region table (see [01-hardware.md](01-hardware.md), section 2):
PRCT size `0x9D000`, VM `0x9D000`/`0x23000`, BTIF `0xC0000`, USRTRIM `0xC1000`, USRFLASH `0xC2000`/`0x29000`
and USR `0xF4000`/`0xA000`, with the stock flags. The app image must fit the app slot. The reference port links
with an XIP length of `0x97400` (the stock app's size).

## 3. Full flash backup (do this first)

You need:

- [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool) (Python 3). It talks to the mask-ROM bootloader
  through raw SCSI commands, so it needs root on Linux and an elevated shell on Windows.
- A custom SMK package, for example a build of the reference port.
- A host tool that can run the check step of an update and then send one SysEx message. Felucca's and SLOOP's
  installers contain all the building blocks: package loading, device search and the check step.

### 3.1 Method A: before anything is installed (preferred)

1. Connect the SMK-37 over USB and close every other program that uses its MIDI port.
2. Run **only the check step** with the custom package: identity query, enter upgrade, serve the reads. The stock
   app accepts the package and resets into the custom update loader. Its identity is now `ota-SMK-37 Pro_9xx`.
   Nothing in the app area has been rewritten at this point.
3. Send the loader the UBOOT soft key `F0 22 24 35 7D F7`. The keyboard re-enumerates as a USB mass-storage
   device named **`WL82 UBOOT1.00`**. **Verified on the tested unit.**
4. Find the device: `/dev/sgN` on Linux, or `\\.\PhysicalDriveN` on Windows (the disk named `WL82 UBOOT`).
5. Read the whole flash twice:

   ```
   python3 jluboottool.py --device <device> --chip wl82 "read 0 0x100000 smk37-dump-1.bin"
   python3 jluboottool.py --device <device> --chip wl82 "read 0 0x100000 smk37-dump-2.bin"
   ```

   The tool prints the flash id when it connects. Note it down (the tested unit reports `0xeb6014`).
6. Check the dumps:
   - both are exactly 1048576 bytes,
   - both have the same SHA-256,
   - offset `0xC1224` holds the 7 characters `trimdat`.

   If any check fails, do not trust the dump. Read again.
7. Keep the dump in at least two places. The ranges `0xC0000-0xC1FFF` (Bluetooth pairing and calibration) and
   `0xFF000-0xFFFFF` (key_mac) are unique to your unit.
8. Power-cycle the keyboard. It comes back in the custom loader's update mode, because the update record is
   still there. Either finish the install of the custom package, or install the stock package to stay stock.

### 3.2 Method B: after a custom firmware is installed

The SLOOP-based firmware can enter the mask-ROM bootloader by itself: hold OCTAVE- and OCTAVE+ for 5 seconds
while the sequencer is stopped, or type `uboot yes` in the USB serial console. Then follow steps 4 to 8 above.

A dump made this way no longer contains the stock app area, but it still contains the unit-unique ranges,
because a correct port never writes them. The stock app area can always be restored from the stock package.

## 4. Installing a custom firmware

1. Build the package for the SMK (see [03-porting-steps.md](03-porting-steps.md)). The reference build writes
   `build/sloop-smk37.fwsc`, identity `SMK-37 Pro_900`.
2. Install with the firmware's own installer (command line or web). The installer must:
   - accept MIDI ports named `SMK...`,
   - accept the `SMK-37 Pro` model and refuse a package for another model,
   - accept the loader identity `ota-SMK-37 Pro_9xx`.
3. Leave the keyboard alone until it restarts into the new firmware.

Interrupted? Power-cycle and run the installer again. The loader resumes.

First boot: the port checks the store's owner tag (`0xAF000`). Data without the port's tag is another firmware's,
so it is cleared: with `FELUCCA_DATA_UNTAGGED_OK 0` that includes the stock firmware's settings (`0x9D000-0xAEFFF`
and `0xB0000`). The calibration, Bluetooth data and the stock resources are not touched, and the stock firmware
rebuilds its settings after a return to stock. Tell the owner before the first install.

## 5. Recovery

From mild to severe:

| Situation | What to do |
|---|---|
| Install interrupted (power loss, cable) | Power-cycle. The custom loader starts again. Run the installer again. |
| New firmware crashes at boot | The SLOOP-based firmware counts failed boots. After two it opens a USB recovery screen (identity `SMK-37 Pro_000`) that accepts a new package. After a third it drops into the mask-ROM bootloader. |
| Firmware runs, but you want the mask-ROM bootloader | Hold OCTAVE- + OCTAVE+ for 5 s while stopped, or use the console command `uboot yes`. |
| Nothing responds over USB MIDI | If the second-stage bootloader or the app header is broken, the mask ROM enters UBOOT by itself. If not, use a JieLi USB_KEY dongle (an RP2040 that pulses the boot key on the USB data lines at power-up): [FM-1 Transporter](https://github.com/kurogedelic/FM-1-transporter), [MvaveFM1Unbricker](https://github.com/Quixotic7/MvaveFM1Unbricker). These were built for the FM-1. The SMK-37 Pro has the same chip and boot ROM, but a dongle has not been tried on it yet. |

### 5.1 Writing flash in the mask-ROM bootloader

`jl-uboot-tool` can erase and write any range. Rules:

- **Never write `0x0000-0x3FFF`, `0xC0000-0xC1FFF` or `0xFF000-0xFFFFF`.** Restore them only from your own
  dump, and only if they were damaged.
- Work in whole 4 KiB sectors. Erase a range, then write it, then read it back and compare.
- To put the stock app back, write the range `0x4000-0x9CFFF` from your Method A dump. Without such a dump,
  install the stock package normally instead. The package's `flash.bin` is the encrypted image as it lies in
  flash.

```
python3 jluboottool.py --device <device> --chip wl82 "erase 0x4000 0x99000"
python3 jluboottool.py --device <device> --chip wl82 "write 0x4000 app-area.bin"
python3 jluboottool.py --device <device> --chip wl82 "read 0x4000 0x99000 check.bin"
```

`app-area.bin` is the byte range `0x4000..0x9CFFF` cut from your dump. Exit UBOOT by power-cycling.

## 6. Return to stock

1. Get the official firmware package for your model from M-Vave. The community repository
   [smk-37-pro-docs](https://github.com/jonathaslacerda/smk-37-pro-docs) keeps a history of the stock versions.
2. Install it the same way as any package:
   - with M-Vave's own updater, or
   - with a Felucca/SLOOP-style installer that handles the 36-block container (section 2.2). Such installers
     refuse packages without their own loader marker unless forced (`--force` in the SLOOP command-line
     installer).
3. The stock firmware boots with your calibration intact, because the custom firmware never wrote USRTRIM.

**Data left behind.** The reference port keeps user samples in the USRFLASH range (`0xC2000-0xE9FFF`) and its
projects in VM (`0x9D000-0xBFFFF`). The stock firmware finds foreign data there after a return. It is not yet
known whether it reformats these areas by itself. For a clean state, write these ranges back from your Method A
dump in the mask-ROM bootloader, or erase them to `0xFF`.

When a SLOOP-based firmware installs the stock package, it accepts the official loader only if the package's
first 16 KiB equal the device's flash head. A custom firmware never writes that range, so the check passes. It
also writes the stock update record name (`ota-SMK-37 Pro_016`), so the official loader comes up under the
name M-Vave's tools expect.
