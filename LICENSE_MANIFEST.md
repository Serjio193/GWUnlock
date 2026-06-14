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
- `licenses/mingw-runtime/COPYING3.txt`
- `licenses/mingw-runtime/COPYING3.LIB.txt`
- `licenses/mingw-runtime/COPYING.RUNTIME.txt`

Detected bundled runtime binaries:

- [x] `dist/GWUnlock.exe`
- [x] `release/GWUnlock.exe`
- [x] `vendor/openocd/bin/openocd.exe`
- [x] `vendor/openocd/bin/libusb-1.0.dll`
- [x] `vendor/openocd/bin/libhidapi-0.dll`
- [x] `vendor/openocd/bin/libjaylink-0.dll`
- [x] `vendor/openocd/bin/libgcc_s_sjlj-1.dll`
- [x] `vendor/openocd/bin/libwinpthread-1.dll`

Runtime dependency license status:

- [x] OpenOCD license notice included: `licenses/openocd/COPYING.txt`.
- [x] libusb runtime binary detected; license notice included: `licenses/libusb/COPYING.txt`.
- [x] hidapi runtime binary detected; license notices included: `licenses/hidapi/LICENSE.txt` and `licenses/hidapi/LICENSE-bsd.txt`.
- [x] libjaylink runtime binary detected; license notice included: `licenses/libjaylink/COPYING.txt`.
- [x] MinGW/GCC runtime DLLs detected: `libgcc_s_sjlj-1.dll` and `libwinpthread-1.dll`.
- [x] MinGW/GCC runtime license notices included under `licenses/mingw-runtime/`.

Needs verification before each public binary release:

- [ ] Generate and review `pip-freeze.txt` or `pip-list.txt` from the exact build environment.
- [ ] Check PyInstaller build output for any additional `.dll`, `.pyd`, `.exe`, `.whl`, or `.zip` files not listed above.
- [ ] Confirm the release ZIP includes `GWUnlock.exe`, `THIRD_PARTY_NOTICES.md`, and the full `licenses/` directory.
