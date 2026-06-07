from __future__ import annotations

import sys

from gnwmanager.ocdbackend.pyocd_backend import PyOCDBackend


OPTSR_CUR_RDP = 0x5200201D


def main(argv: list[str]) -> int:
    frequency = int(argv[1], 0) if len(argv) > 1 else 8_000_000
    backend = PyOCDBackend(connect_mode="under-reset")
    try:
        backend.open()
        backend.set_frequency(frequency)
        rdp = backend.read_memory(OPTSR_CUR_RDP, 1)[0]
        print(f"RDP: 0x{rdp:02X}")
        if rdp == 0xAA:
            print("Protection: UNLOCKED")
        else:
            print("Protection: LOCKED")
        return 0
    except Exception as exc:
        print(f"Protection check failed: {exc}")
        print("Protection: UNKNOWN")
        return 1
    finally:
        try:
            backend.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
