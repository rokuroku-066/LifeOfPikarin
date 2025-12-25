#!/usr/bin/env python3
"""Generate placeholder Phase 2 viewer assets (GLB + textures)."""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


def build_minimal_glb() -> bytes:
    json_str = '{"asset":{"version":"2.0"}}'
    padding = (4 - len(json_str) % 4) % 4
    json_bytes = json_str.encode("utf-8") + b" " * padding
    json_length = len(json_bytes)
    total_length = 12 + 8 + json_length
    header = struct.pack("<III", 0x46546C67, 2, total_length)
    chunk_header = struct.pack("<I4s", json_length, b"JSON")
    return header + chunk_header + json_bytes


def build_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    r, g, b = color
    row = bytes([r, g, b]) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    compressed = zlib.compress(raw)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(
        b"IEND", b""
    )


def write_asset(path: Path, data: bytes, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Use --overwrite to replace.")
    path.write_bytes(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate placeholder Phase 2 assets (GLB + textures)."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/terrarium/app/static/assets"),
        help="Directory to write assets into.",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    write_asset(output_dir / "pikarin.glb", build_minimal_glb(), args.overwrite)
    write_asset(output_dir / "ground.png", build_png(4, 4, (120, 120, 120)), args.overwrite)
    write_asset(output_dir / "wall_back.png", build_png(4, 4, (160, 160, 170)), args.overwrite)
    write_asset(output_dir / "wall_side.png", build_png(4, 4, (150, 140, 130)), args.overwrite)

    print(f"Generated dummy assets in {output_dir}")


if __name__ == "__main__":
    main()
