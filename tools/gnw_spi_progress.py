from __future__ import annotations

import argparse
import time
from collections import namedtuple
from pathlib import Path

from gnwmanager.gnw import GnW, chunk_bytes, pad_bytes, sha256
from gnwmanager.ocdbackend.pyocd_backend import PyOCDBackend


def open_gnw(frequency: int) -> GnW:
    backend = PyOCDBackend(connect_mode="under-reset")
    backend.open()
    backend.set_frequency(frequency)
    gnw = GnW(backend)
    gnw.start_gnwmanager()
    return gnw


def emit(kind: str, progress: int, done: int, total: int, started: float) -> None:
    elapsed = max(time.perf_counter() - started, 0.001)
    speed = done / elapsed
    print(f"GNW_{kind}_PROGRESS {progress} {done} {total} {speed:.0f}", flush=True)


def read_ext(args: argparse.Namespace) -> None:
    gnw = open_gnw(args.frequency)
    total = args.size or int(gnw.external_flash_size)
    print(f"GNW_FLASH_SIZE {total}", flush=True)
    chunk = max(4096, args.chunk)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    started = time.perf_counter()
    done = 0
    emit("READ", 0, 0, total, started)
    with out.open("wb") as handle:
        while done < total:
            size = min(chunk, total - done)
            handle.write(gnw.read_memory(0x90000000 + done, size))
            done += size
            emit("READ", int(done * 100 / total), done, total, started)
    print(f"GNW_READ_DONE {time.perf_counter() - started:.3f}", flush=True)


def verify_ext(gnw: GnW, offset: int, chunks: list[bytes], chunk_size: int, started: float) -> None:
    total_bytes = sum(len(chunk) for chunk in chunks)
    done = 0
    emit("VERIFY", 0, 0, total_bytes, started)
    group_size = max(1, (2 << 20) // chunk_size)
    for start in range(0, len(chunks), group_size):
        group = chunks[start:start + group_size]
        expected = [sha256(chunk) for chunk in group]
        size = sum(len(chunk) for chunk in group)
        actual = gnw.read_hashes(offset + start * chunk_size, size)
        if actual[:len(expected)] != expected:
            raise RuntimeError(f"verify failed at external flash offset 0x{offset + start * chunk_size:08X}")
        done += size
        emit("VERIFY", int(done * 100 / total_bytes), done, total_bytes, started)
    print(f"GNW_VERIFY_DONE {time.perf_counter() - started:.3f}", flush=True)


def write_ext(args: argparse.Namespace) -> None:
    gnw = open_gnw(args.frequency)
    source = Path(args.input)
    data = pad_bytes(source.read_bytes(), int(gnw.external_flash_block_size))
    if len(data) > int(gnw.external_flash_size):
        raise ValueError("input does not fit into external flash")

    started = time.perf_counter()
    print(f"GNW_WRITE_HASH_START {len(data)}", flush=True)
    hash_started = time.perf_counter()
    device_hashes = gnw.read_hashes(args.offset, len(data))
    print(f"GNW_WRITE_HASH_DONE {time.perf_counter() - hash_started:.3f}", flush=True)

    chunk_size = gnw.contexts[0]["buffer"].size
    chunks = chunk_bytes(data, chunk_size)
    Packet = namedtuple("Packet", ["addr", "data"])
    all_packets = [Packet(args.offset + i * chunk_size, chunk) for i, chunk in enumerate(chunks)]
    packets = [
        packet
        for packet, device_hash in zip(all_packets, device_hashes)
        if sha256(packet.data) != device_hash
    ]
    total = len(packets)
    print(f"GNW_WRITE_PACKETS {total} {len(all_packets)} {chunk_size}", flush=True)
    if total == 0:
        print(f"GNW_WRITE_DONE {time.perf_counter() - started:.3f} skipped", flush=True)
        verify_ext(gnw, args.offset, chunks, chunk_size, started)
        return

    emit("WRITE", 0, 0, total, started)
    written = 0
    total_bytes = sum(len(packet.data) for packet in packets)
    for idx, packet in enumerate(packets, start=1):
        gnw.program(0, packet.addr, packet.data, blocking=False)
        gnw.write_uint32("progress", int(26 * idx / total))
        gnw.wait_for_all_contexts_complete()
        written += len(packet.data)
        emit("WRITE", int(idx * 100 / total), written, total_bytes, started)
    print(f"GNW_WRITE_DONE {time.perf_counter() - started:.3f}", flush=True)
    verify_ext(gnw, args.offset, chunks, chunk_size, started)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency", type=int, default=8_000_000)
    sub = parser.add_subparsers(dest="command", required=True)

    read = sub.add_parser("read-ext")
    read.add_argument("--output", required=True)
    read.add_argument("--size", type=int, default=0)
    read.add_argument("--chunk", type=int, default=2 << 20)
    read.set_defaults(func=read_ext)

    write = sub.add_parser("write-ext")
    write.add_argument("--input", required=True)
    write.add_argument("--offset", type=int, default=0)
    write.set_defaults(func=write_ext)

    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        message = str(exc)
        print(f"GNW_ERROR {type(exc).__name__}: {message}", flush=True)
        if "DP error" in message or "STLink error" in message or "TransferError" in type(exc).__name__:
            print("GNW_HINT ST-Link lost the debug connection while accessing the device.", flush=True)
            print("GNW_HINT Power-cycle the device, wait two seconds, select 4000 or 2000 kHz, and repeat the step.", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
