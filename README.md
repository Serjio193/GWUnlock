# GWUnlock

GWUnlock is a standalone Windows utility for Nintendo Game & Watch devices based on the STM32H7B0 microcontroller.

## Features

- Device identification
- SPI Flash backup and restore
- Internal MCU Flash backup and restore
- Device information display
- ST-Link support
- Portable single-file executable
- Light and dark UI themes
- English, Russian, and Ukrainian interface languages

## Requirements

- Windows 10 x64 or Windows 11 x64
- ST-Link V2 or compatible programmer
- ST-Link USB driver

Python, PySide6, OpenOCD, pyOCD, and gnwmanager are bundled in the portable release executable.

## Usage Notes

GWUnlock stores device backup files next to the executable in the `backups` folder.

Keep this folder in a safe place. Restore requires the matching SPI backup, MCU backup, and ITCM backup from the same device.

The single-file executable may temporarily extract runtime files into a `_MEI...` folder while it is running. This is normal for PyInstaller one-file applications. Backup files are not stored there.

## Build

Install project dependencies in a local Python environment, then build with PyInstaller:

```powershell
python -m PyInstaller --noconfirm GWUnlock.spec
```

The resulting executable is created under `dist`.

## Notes

GWUnlock is intended for backup, restore, research, and educational purposes. Users are responsible for complying with all applicable laws and regulations in their jurisdiction.

## Credits

This project was inspired by research and community work surrounding Nintendo Game & Watch devices, including:

- ghidraninja/game-and-watch-backup
- ghidraninja/game-and-watch-hacking
- BrianPugh/gnwmanager
- The Game & Watch modding community

## Благодарности

Проект вдохновлён исследованиями и работой:

- ghidraninja/game-and-watch-backup
- ghidraninja/game-and-watch-hacking
- Сообществом модификации Nintendo Game & Watch

## Third-Party Components

- Python
- PySide6 (Qt for Python)
- OpenOCD
- pyOCD
- gnwmanager

## Disclaimer

This project is not affiliated with or endorsed by Nintendo, STMicroelectronics, or any other company mentioned above.
