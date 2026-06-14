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

Repository license file layout:

- `licenses/python/LICENSE.txt`
- `licenses/pyside6/LICENSE.LGPL3.txt`
- `licenses/pyside6/LICENSE.GPL2.txt`
- `licenses/pyside6/LICENSE.GPL3.txt`
- `licenses/pyinstaller/COPYING.txt`
- `licenses/pyinstaller/BOOTLOADER_EXCEPTION.txt`
- `licenses/gnwmanager/LICENSE.txt`
- `licenses/pyocd/LICENSE.txt`
- `licenses/openocd/COPYING.txt`
- `licenses/libusb/COPYING.txt`
- `licenses/hidapi/LICENSE.txt`
- `licenses/hidapi/LICENSE-bsd.txt`
- `licenses/libjaylink/COPYING.txt`
- `licenses/mingw-runtime/README.txt`

Needs verification from exact build/release files:

- [ ] libusb license file from exact OpenOCD package.
- [x] hidapi license files from upstream hidapi repository.
- [x] libjaylink COPYING file from upstream libjaylink mirror.
- [ ] libgcc / winpthread / MinGW runtime license files from the exact OpenOCD package, if present.
- [ ] Any additional Python package licenses from `pip freeze` / PyInstaller analysis output.
