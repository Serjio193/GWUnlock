from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path


BLOCK_SIZE = 16
MODEL_ITCM = {
    "mario": (0, 1300, "ca71a54c0a22cca5c6ee129faee9f99f3a346ca0"),
    "zelda": (0x20, 1300, "2f70156235ffd871599facf64457040d549353b4"),
}
MODEL_SPI = {
    "mario": (0, 65024 * 16, "eea70bb171afece163fb4b293c5364ddb90637ae"),
    "zelda": (8192 * 16, 197962 * 16, "1c1c0ed66d07324e560dcd9e86a322ec5e4c1e96"),
}


def _read_sha1_file(path: Path) -> tuple[str, Path]:
    line = path.read_text(encoding="utf-8").strip().splitlines()[0]
    parts = line.split()
    if len(parts) < 2:
        raise ValueError(f"Invalid sha1 file: {path}")
    return parts[0].lower(), Path(parts[1])


def verify(sha1_path: Path) -> int:
    expected, payload_path = _read_sha1_file(sha1_path)
    if not payload_path.exists():
        print(f"Missing file: {payload_path}")
        return 1

    digest = hashlib.sha1()
    with payload_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    actual = digest.hexdigest().lower()
    if actual != expected:
        print(f"SHA1 mismatch for {payload_path}")
        print(f"expected {expected}")
        print(f"actual   {actual}")
        return 1
    print(f"SHA1 OK: {payload_path}")
    return 0


def slice_file(src: Path, dst: Path, skip_16: int, count_16: int) -> int:
    if not src.exists():
        print(f"Missing file: {src}")
        return 1
    offset = skip_16 * BLOCK_SIZE
    size = count_16 * BLOCK_SIZE
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as source:
        source.seek(offset)
        data = source.read(size)
    if len(data) != size:
        print(f"Short read from {src}: got {len(data)}, expected {size}")
        return 1
    dst.write_bytes(data)
    print(f"Wrote {dst} ({size} bytes)")
    return 0


def concat(output: Path, *parts: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as dst:
        for part in parts:
            if not part.exists():
                print(f"Missing part: {part}")
                return 1
            with part.open("rb") as src:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    dst.write(chunk)
    print(f"Wrote {output} ({output.stat().st_size} bytes)")
    return 0


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def sha1_command(path: Path) -> int:
    if not path.exists():
        print(f"Missing file: {path}")
        return 1
    print(f"SHA1 {path} {file_sha1(path)}")
    return 0


def verify_digest(path: Path, expected: str) -> int:
    if not path.exists():
        print(f"Missing file: {path}")
        return 1
    actual = file_sha1(path)
    if actual != expected.lower():
        print(f"SHA1 mismatch for {path}")
        print(f"expected {expected.lower()}")
        print(f"actual   {actual}")
        return 1
    print(f"SHA1 OK: {path}")
    return 0


def has_valid_stm32_vector(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 8:
        return False
    header = path.read_bytes()[:8]
    sp, pc = struct.unpack("<II", header)
    valid_sp = 0x20000000 <= sp < 0x30000000
    valid_pc = 0x08000000 <= pc < 0x08200000
    if not valid_sp or not valid_pc:
        print(f"Invalid STM32 vector table in {path}: SP=0x{sp:08x} PC=0x{pc:08x}")
        return False
    print(f"STM32 vector OK: SP=0x{sp:08x} PC=0x{pc:08x}")
    return True


def validate_internal(path: Path) -> int:
    if not path.exists():
        print(f"Missing file: {path}")
        return 1
    size = path.stat().st_size
    if size != 131072:
        print(f"Unexpected internal flash size: {size}. Expected 131072 bytes.")
        return 1
    if not has_valid_stm32_vector(path):
        return 1
    data = path.read_bytes()
    if data == b"\x00" * len(data) or data == b"\xff" * len(data):
        print("Internal flash image is blank; refusing to accept it.")
        return 1
    print(f"Internal flash image OK: {path}")
    return 0


def describe_file(path: Path, label: str = "file") -> int:
    if not path.exists():
        print(f"{label} missing: {path}")
        return 1
    size = path.stat().st_size
    sha1 = file_sha1(path)
    print(f"{label} path={path.resolve()}")
    print(f"{label} size={size}")
    print(f"{label} sha1={sha1}")
    if size >= 8:
        sp, pc = struct.unpack("<II", path.read_bytes()[:8])
        print(f"{label} vector_sp=0x{sp:08x}")
        print(f"{label} vector_pc=0x{pc:08x}")
    return 0


def compare_files(expected: Path, actual: Path, label: str = "compare") -> int:
    if not expected.exists() or not actual.exists():
        print(f"{label} missing file: expected={expected} actual={actual}")
        return 1
    expected_sha1 = file_sha1(expected)
    actual_sha1 = file_sha1(actual)
    print(f"{label} expected_path={expected.resolve()}")
    print(f"{label} actual_path={actual.resolve()}")
    print(f"{label} expected_size={expected.stat().st_size}")
    print(f"{label} actual_size={actual.stat().st_size}")
    print(f"{label} expected_sha1={expected_sha1}")
    print(f"{label} actual_sha1={actual_sha1}")
    if expected_sha1 != actual_sha1 or expected.stat().st_size != actual.stat().st_size:
        print(f"{label} result=DIFFER")
        return 1
    print(f"{label} result=MATCH")
    return 0


def stable_copy(first: Path, second: Path, marker: Path, actual_sha1: Path) -> int:
    if not first.exists() or not second.exists():
        print("Missing file for stable backup comparison.")
        return 1
    first_size = first.stat().st_size
    second_size = second.stat().st_size
    if first_size != 131072 or second_size != 131072:
        print(f"Unexpected internal backup size: {first_size} and {second_size}")
        return 1
    first_sha1 = file_sha1(first)
    second_sha1 = file_sha1(second)
    print(f"First internal backup SHA1  {first_sha1}")
    print(f"Second internal backup SHA1 {second_sha1}")
    if first_sha1 != second_sha1:
        print("Internal backup is not stable; two dumps differ.")
        return 1
    if validate_internal(first) != 0:
        print("Internal backup is stable but not a valid STM32 firmware image.")
        return 1
    data = first.read_bytes()
    if data == b"\x00" * len(data) or data == b"\xff" * len(data):
        print("Internal backup is blank; refusing to accept it.")
        return 1
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(first_sha1 + "\n", encoding="ascii")
    actual_sha1.write_text(f"{first_sha1}  {first.as_posix()}\n", encoding="ascii")
    print("Internal backup accepted by stable duplicate verification.")
    return 0


def detect_model(path: Path) -> int:
    if not path.exists():
        print(f"Model detection file is missing: {path}")
        return 1
    data = path.read_bytes()
    for model, (offset, length, expected) in MODEL_ITCM.items():
        end = offset + length
        if len(data) >= end and hashlib.sha1(data[offset:end]).hexdigest() == expected:
            print(f"Detected model: {model}")
            return 0
    print("Detected model: unknown")
    return 1


def detect_model_spi(path: Path) -> int:
    if not path.exists():
        print(f"Detected model: unknown")
        return 1
    with path.open("rb") as handle:
        for model, (offset, length, expected) in MODEL_SPI.items():
            handle.seek(offset)
            if hashlib.sha1(handle.read(length)).hexdigest() == expected:
                print(f"Detected model: {model}")
                return 0
    print("Detected model: unknown")
    return 1


def verify_model_itcm(path: Path, model: str) -> int:
    config = MODEL_ITCM.get(model.lower())
    if config is None or not path.exists():
        print(f"Invalid {model} ITCM reference: {path}")
        return 1
    _, length, expected = config
    data = path.read_bytes()
    actual = hashlib.sha1(data[:length]).hexdigest()
    if len(data) != length or actual != expected:
        print(f"Invalid {model} ITCM reference: {path}")
        return 1
    print(f"Valid {model} ITCM reference: {path}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: win_ops.py verify <sha1-file> | verify-digest <file> <sha1> | verify-model-itcm <file> <model> | detect-model <itcm-probe> | detect-model-spi <spi-backup> | sha1 <file> | describe-file <file> [label] | compare-files <expected> <actual> [label] | validate-internal <file> | stable-internal <first> <second> <marker> <actual-sha1> | slice <src> <dst> <skip16> <count16> | concat <output> <part...>")
        return 2
    command = argv[1].lower()
    if command == "verify" and len(argv) == 3:
        return verify(Path(argv[2]))
    if command == "slice" and len(argv) == 6:
        return slice_file(Path(argv[2]), Path(argv[3]), int(argv[4], 0), int(argv[5], 0))
    if command == "concat" and len(argv) >= 4:
        return concat(Path(argv[2]), *[Path(arg) for arg in argv[3:]])
    if command == "sha1" and len(argv) == 3:
        return sha1_command(Path(argv[2]))
    if command == "verify-digest" and len(argv) == 4:
        return verify_digest(Path(argv[2]), argv[3])
    if command == "validate-internal" and len(argv) == 3:
        return validate_internal(Path(argv[2]))
    if command == "describe-file" and len(argv) in (3, 4):
        return describe_file(Path(argv[2]), argv[3] if len(argv) == 4 else "file")
    if command == "compare-files" and len(argv) in (4, 5):
        return compare_files(Path(argv[2]), Path(argv[3]), argv[4] if len(argv) == 5 else "compare")
    if command == "stable-internal" and len(argv) == 6:
        return stable_copy(Path(argv[2]), Path(argv[3]), Path(argv[4]), Path(argv[5]))
    if command == "detect-model" and len(argv) == 3:
        return detect_model(Path(argv[2]))
    if command == "detect-model-spi" and len(argv) == 3:
        return detect_model_spi(Path(argv[2]))
    if command == "verify-model-itcm" and len(argv) == 4:
        return verify_model_itcm(Path(argv[2]), argv[3])
    print("Invalid arguments.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
