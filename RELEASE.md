# Release Notes

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
