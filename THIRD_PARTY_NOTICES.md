# Third-Party Notices

GWUnlock release binaries bundle third-party runtime components inside the executable. This file is a summary for release users and does not replace the full upstream license texts.

The main GWUnlock source code is released under the Unlicense. Third-party components bundled inside the executable remain under their own respective licenses.

## Important Packaging Note

GWUnlock is distributed as a portable Windows executable. Required runtime components are bundled inside `GWUnlock.exe`.

The ST-Link USB driver is **not** bundled with GWUnlock and must be installed separately by the user from the official vendor/source.

## Bundled Components

| Component | Version | License | Project / Source |
|---|---:|---|---|
| Python | 3.13.2 | Python Software Foundation License Version 2 | https://www.python.org/ |
| PySide6 / Qt for Python | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | https://pyside.org/ |
| PyInstaller | 6.19.0 | GPL-2.0-or-later with PyInstaller bootloader exception | https://pyinstaller.org/ |
| gnwmanager | 0.21.1 | Apache-2.0 | https://github.com/BrianPugh/gnwmanager |
| pyOCD | 0.44.1 | Apache-2.0 | https://github.com/pyocd/pyOCD |
| OpenOCD | 0.12.0+dev-00645-g2306f32ee | GPL-2.0-or-later | https://openocd.org/ |

## OpenOCD Runtime Dependencies

The bundled OpenOCD runtime may include DLLs and runtime libraries inside the executable, including but not limited to:

- libusb
- hidapi
- libjaylink
- libgcc
- winpthread / winpthreads

These components are distributed under their respective upstream licenses. If you redistribute GWUnlock binaries, keep the OpenOCD license notices and dependency license notices with the release package.

Exact dependency license files may vary depending on the OpenOCD build used. Verify the actual OpenOCD package bundled into GWUnlock before publishing a final release.

## Qt / PySide6 LGPL Notice

GWUnlock uses PySide6 / Qt for Python under the LGPL option. Users must not be prevented from replacing or relinking the LGPL-covered Qt/PySide6 components where technically applicable.

The upstream Qt for Python project and license information is available at:

- https://doc.qt.io/qtforpython-6/
- https://www.qt.io/licensing/open-source-lgpl-obligations

## Firmware / ROM Disclaimer

GWUnlock does not include, distribute, or provide Nintendo firmware, ROMs, BIOS files, game data, copyrighted images, or other proprietary Nintendo content.

Users are responsible for creating and preserving backups from their own devices and for complying with all applicable laws and regulations in their jurisdiction.

## Affiliation Disclaimer

This project is not affiliated with, endorsed by, or associated with Nintendo, STMicroelectronics, Qt Group, OpenOCD, or any other company or upstream project mentioned in this repository.

## Full License Texts

Full license texts for bundled third-party components are included in the `licenses/` directory and should be distributed together with binary releases.
