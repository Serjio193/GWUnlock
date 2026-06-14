# Release Notes

## v1.0.9

Complete bundled license texts.

- Replace shortened Python license file with the full CPython 3.13.2 license text.
- Replace PyInstaller GPL text with the upstream PyInstaller 6.19.0 `COPYING.txt`.
- Add PySide6 license aliases: `LICENSE.LGPL3.txt`, `LICENSE.GPL2.txt`, and `LICENSE.GPL3.txt`.
- Add upstream hidapi `LICENSE.txt` and `LICENSE-bsd.txt`.
- Add libjaylink `COPYING.txt`.
- Replace the MinGW runtime placeholder with a verification README describing the bundled runtime DLLs.
- Update license manifest and third-party notices to match the actual repository layout.

SHA256:

```text
C9A45813AD70435717723810A3400734DEAF0050DFBE79A5672CDB553FC48C75  GWUnlock.exe
BBF7816C29B775F397589FB76E4C194AD028018C607F926CB3681FD0B88F12D1  GWUnlock-v1.0.9-windows-x64.zip
```

## v1.0.8

License file layout compatibility.

- Add canonical license aliases under `licenses/`, including `licenses/python/LICENSE.txt` and `licenses/pyinstaller/COPYING.txt`.
- Add common `LICENSE.txt` / `COPYING.txt` aliases for bundled Apache/GPL/LGPL components.
- Update `LICENSE_MANIFEST.md` with the expected repository license paths.

SHA256:

```text
01708EC0FC98443BFCB6DE82A88707265C8A4F9200BF208DE029E95DBD10306E  GWUnlock.exe
ED69FB0F94B0956CDC649633E321BE5CF004A916D0683AA2FD875E9F8AE9B5D6  GWUnlock-v1.0.8-windows-x64.zip
```

## v1.0.7

License pack integration.

- Add full third-party license text directory under `licenses/`.
- Add `LICENSE_MANIFEST.md` and release packing instructions.
- Include license notices and license texts in the PyInstaller bundle.
- Update README with explicit license distribution notes.
- Prepare release ZIP packaging with EXE, SHA256, notices, manifest, and full license texts.

SHA256:

```text
1CBD488CED5D67A58BA26142EECCF7A8631AA44CD4D62EC3D4A83E6B24199054  GWUnlock.exe
1FA8F1D41EF1FC3B6C6E328C05AEB8AD7DFC9A0F5F52180A74A544ABBC748794  GWUnlock-v1.0.7-windows-x64.zip
```

## v1.0.6

Version status, updater restart, and restore validation.

- Show the current GWUnlock version in the top-right corner.
- Mark the version as latest after a successful update check when no newer release exists.
- Show the available release version when an update is found.
- Start the update installer as a detached process and force-close the old process so the downloaded EXE can replace it.
- Write updater diagnostics to `updates/update.log`.
- Reject empty or non-4096-byte-aligned SPI backup files during restore.

SHA256:

```text
3EC3E0AD23A6262D086D3454BDE428D4D260E4486E13D75C6C869A4ED82A4843  GWUnlock.exe
```

## v1.0.5

Restore compatibility for smaller SPI images.

- Allow Step 5 Restore to use an SPI backup that is smaller than the detected physical SPI flash.
- Keep rejecting SPI backup files that are larger than the detected device flash.
- Log when a smaller image is restored at the SPI base address.

SHA256:

```text
86379AFEFC6A334D7F48165CED6499877E1145421C624FE925EE5F60DE40BCE5  GWUnlock.exe
```

## v1.0.4

Restore button and third-party notices update.

- Allow Step 5 Restore on already-unlocked devices when SPI and MCU backups are present.
- If the stored SPI size marker is missing, Step 5 reads the SPI flash size from the device before restore.
- Keep restore validation tied to the detected device size instead of a hard-coded size.
- Expand `THIRD_PARTY_NOTICES.md` with component versions, licenses, upstream links, OpenOCD runtime dependencies, Qt/PySide6 LGPL notice, and firmware/ROM disclaimer.

SHA256:

```text
11B6C849D63747F4E2F66FAFB0EA7555A40B70FE314C71BD004117D1A4657105  GWUnlock.exe
```

## v1.0.3

Dynamic SPI flash size handling.

- Read SPI flash size during Step 1 and store it next to runtime state.
- Use the detected size for SPI backup, payload programming, and restore.
- Validate SPI backup size against the detected device size instead of a fixed 64 MiB value.
- Block Step 2/3/4 until Step 1 has successfully detected protection and SPI size.

SHA256:

```text
3697A5FA31237BB1070449CD34138F36D1DAB31A13078EFB987F38EAF3E109F0  GWUnlock.exe
```

## v1.0.2

Update checker.

- Check the latest GitHub Release on startup.
- Ask the user before downloading or installing an update.
- Download `GWUnlock.exe` and `GWUnlock.exe.sha256` only after user confirmation.
- Verify the downloaded executable SHA256 before installation.
- Replace the running executable through a local update script after GWUnlock exits.

SHA256:

```text
41FDB0482C57C58BA632BEAA89C5871C25BEF28785CBE3E27AAF2A0933D7E27D  GWUnlock.exe
```

## v1.0.1

Protection and SPI detection fixes.

- Stop Step 1 with an error when protection status is `UNKNOWN`.
- Block Step 2/3/4 until Step 1 completes successfully.
- Show a clear power/SWD/ST-Link connection hint when protection cannot be read.
- Detect and display the SPI flash size through `gnwmanager` instead of printing a hard-coded size before detection.
- Improve Step 2 error explanation for `STLink Get IDCODE` failures.

SHA256:

```text
7D03861F419839F0B004CF8BA6F14D955AB8C16FA9DA68DD7E40F0055D22BE47  GWUnlock.exe
```

## v1.0.0

Initial public release of GWUnlock.

- Standalone Windows x64 utility.
- Device identification and protection status display.
- SPI Flash backup and restore.
- Internal MCU Flash backup and restore.
- ST-Link support.
- Portable single-file executable.
- Light and dark UI themes.
- English, Russian, and Ukrainian interface languages.

SHA256:

```text
6ECB241B2E9DEF780ACD3D548C8F960DAB3FA3B80FECB4809B5FE926D10BC3D8  GWUnlock.exe
```

## Release Process

The portable executable is produced by PyInstaller and should be uploaded as a GitHub Release asset.

Current local artifact:

```text
release/GWUnlock.exe
release/GWUnlock.exe.sha256
```

Do not commit large executable files into git history.

Every new release must use a new semantic version tag, for example `v1.0.1`, `v1.1.0`, or `v2.0.0`, and must include a short release description.
