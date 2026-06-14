# GWUnlock Release Packing Instructions

Recommended GitHub Release asset:

```text
GWUnlock-vX.Y.Z-windows-x64.zip
  GWUnlock.exe
  THIRD_PARTY_NOTICES.md
  licenses/
    python/
    pyside6/
    pyinstaller/
    pyocd/
    gnwmanager/
    openocd/
    libusb/
    hidapi/
    libjaylink/
    mingw-runtime/
```

Do not publish only a bare `GWUnlock.exe` as the only release asset. Keep the program portable, but ship the notices and license texts in the release archive.

Before publishing a final release, verify the exact OpenOCD binary package used in the build and copy its original license/notice files into the matching folders under `licenses/`.
