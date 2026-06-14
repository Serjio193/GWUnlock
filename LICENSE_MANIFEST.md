# License Manifest Checklist

Confirmed by current GWUnlock documentation:

- [x] GWUnlock source code: Unlicense, see repository `LICENSE`.
- [x] Python: bundled runtime component.
- [x] PySide6 / Qt for Python: bundled runtime component.
- [x] PyInstaller: used for one-file executable.
- [x] gnwmanager: bundled component.
- [x] pyOCD: bundled component.
- [x] OpenOCD: bundled component.
- [x] ST-Link USB driver: not bundled; user installs separately.

Needs verification from exact build/release files:

- [ ] libusb license file from exact OpenOCD package.
- [ ] hidapi license file from exact OpenOCD package.
- [ ] libjaylink license file from exact OpenOCD package, if present.
- [ ] libgcc / winpthread / MinGW runtime license files, if present.
- [ ] Any additional Python package licenses from `pip freeze` / PyInstaller analysis output.
