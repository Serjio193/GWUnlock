# Release Notes

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
