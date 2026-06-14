# Third-Party Notices

GWUnlock uses and bundles third-party components. This file is a summary for release users and does not replace the full upstream license texts. Review each upstream project for complete license terms.

## Bundled Components

- Python, PSF License, https://www.python.org/
- PySide6 / Qt for Python 6.11.1, LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only, https://pyside.org/
- PyInstaller 6.19.0, GPLv2-or-later with the PyInstaller bootloader exception, https://pyinstaller.org/
- gnwmanager 0.21.1, Apache-2.0, https://github.com/BrianPugh/gnwmanager
- pyOCD 0.44.1, Apache-2.0, https://github.com/pyocd/pyOCD
- OpenOCD, GPL-2.0-or-later, https://openocd.org/

## OpenOCD Runtime Dependencies

The bundled OpenOCD runtime may include DLLs and runtime libraries next to `openocd.exe`, including but not limited to:

- libusb
- hidapi
- libjaylink
- libgcc
- winpthread / winpthreads

These components are distributed under their respective upstream licenses. If you redistribute GWUnlock binaries, keep the OpenOCD license notices and dependency license notices with the release package.

## Qt / PySide6 LGPL Notice

GWUnlock uses PySide6 / Qt for Python under the LGPL option. Users must not be prevented from replacing or relinking the LGPL-covered Qt/PySide6 components where technically applicable. The upstream Qt for Python project and license information is available at:

- https://doc.qt.io/qtforpython-6/
- https://www.qt.io/licensing/open-source-lgpl-obligations

## Research References

GWUnlock was inspired by public research and community work around Nintendo Game & Watch devices, including:

- https://github.com/ghidraninja/game-and-watch-backup
- https://github.com/ghidraninja/game-and-watch-hacking
- https://github.com/BrianPugh/gnwmanager

## Firmware / ROM Disclaimer

GWUnlock does not include, distribute, or provide Nintendo firmware, ROMs, BIOS files, game data, copyrighted images, or other proprietary Nintendo content.

Users are responsible for creating and preserving backups from their own devices and for complying with all applicable laws and regulations in their jurisdiction.

## Affiliation Disclaimer

This project is not affiliated with, endorsed by, or associated with Nintendo, STMicroelectronics, Qt Group, OpenOCD, or any other company or upstream project mentioned in this repository.
