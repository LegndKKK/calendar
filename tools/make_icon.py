"""生成应用图标（纯标准库，无需 Pillow）。"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 256


def in_round_rect(x: int, y: int, x0: int, y0: int, x1: int, y1: int, radius: int) -> bool:
    if x < x0 or x >= x1 or y < y0 or y >= y1:
        return False
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def in_circle(x: int, y: int, cx: int, cy: int, radius: int) -> bool:
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def color_at(x: int, y: int) -> tuple[int, int, int, int]:
    if not in_round_rect(x, y, 8, 8, 248, 248, 52):
        return (0, 0, 0, 0)

    color = (79, 70, 229, 255)  # 靛蓝背景

    if in_round_rect(x, y, 40, 68, 216, 220, 18):
        color = (255, 255, 255, 255)  # 日历纸面

    if in_round_rect(x, y, 74, 46, 92, 88, 9) or in_round_rect(x, y, 164, 46, 182, 88, 9):
        color = (199, 210, 254, 255)  # 装订环

    for row in range(4):
        for col in range(4):
            cx = 72 + col * 40
            cy = 116 + row * 26
            if in_circle(x, y, cx, cy, 6):
                color = (245, 158, 11, 255) if (row == 3 and col == 3) else (79, 70, 229, 255)

    return color


def png_bytes() -> bytes:
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)  # filter type 0
        for x in range(SIZE):
            raw.extend(color_at(x, y))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    png = png_bytes()
    ico_header = struct.pack("<HHH", 0, 1, 1)
    ico_entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
    output = Path(__file__).resolve().parent.parent / "static" / "icon.ico"
    output.write_bytes(ico_header + ico_entry + png)
    print(f"已生成 {output}")


if __name__ == "__main__":
    main()
