"""Locate the 2.4 GHz envelope magic inside the official tool and find the code
that references it.

The dongle's 65-byte output report looks like:
    00 BB AA 99 88 AA <e> <b> <s> 00 00 ...
So `BB AA 99 88 AA` must exist as a constant. Finding its xrefs should lead us
to the envelope builder, and whatever other commands live next to it.

Usage: python tools/find_magic.py [exe]
"""
import re
import struct
import sys

import pefile

MAGIC = bytes.fromhex("bbaa9988aa")
DEFAULT_EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXE
    pe = pefile.PE(path, fast_load=True)
    raw = open(path, "rb").read()
    image_base = pe.OPTIONAL_HEADER.ImageBase
    print(f"{path}  imageBase=0x{image_base:x}\n")

    hits = []
    for sec in pe.sections:
        name = sec.Name.rstrip(b"\x00").decode("latin-1")
        data = sec.get_data()
        start = 0
        while True:
            i = data.find(MAGIC, start)
            if i < 0:
                break
            va = image_base + sec.VirtualAddress + i
            hits.append((name, i, va, sec))
            start = i + 1

    if not hits:
        print("没找到完整魔数，看更短片段的上下文：")
        for frag in ("bbaa9988", "bbaa99", "9988aa"):
            b = bytes.fromhex(frag)
            print(f"\n--- {frag} ({raw.count(b)} 次) ---")
            start = 0
            for _ in range(6):
                i = raw.find(b, start)
                if i < 0:
                    break
                start = i + 1
                # which section is it in?
                where = "?"
                for sec in pe.sections:
                    off, sz = sec.PointerToRawData, sec.SizeOfRawData
                    if off <= i < off + sz:
                        where = sec.Name.rstrip(b"\x00").decode("latin-1")
                        break
                ctx = raw[max(0, i - 16):i + 32]
                print(f"  off=0x{i:06x} [{where}]  "
                      f"...{' '.join(f'{x:02x}' for x in ctx)}...")
        return 1

    print(f"找到 {len(hits)} 处魔数：")
    for name, off, va, _sec in hits:
        print(f"  .{name:8s} off=0x{off:06x}  va=0x{va:08x}")

    # references: a 4-byte absolute address (x86 /32-bit build) or a RIP-relative
    # displacement (x64). Try the absolute form first.
    print("\n在 .text 里搜索对该地址的绝对引用（32 位立即数）：")
    text = None
    for sec in pe.sections:
        if sec.Name.rstrip(b"\x00").startswith(b".text"):
            text = sec
    if text is None:
        print("没有 .text 段")
        return 1

    tdata = text.get_data()
    tva = image_base + text.VirtualAddress
    for _name, _off, va, _sec in hits:
        pat = struct.pack("<I", va)
        found = []
        s = 0
        while True:
            i = tdata.find(pat, s)
            if i < 0:
                break
            found.append(tva + i)
            s = i + 1
        print(f"  魔数@0x{va:08x} -> {len(found)} 处引用: " +
              (", ".join(f"0x{a:08x}" for a in found[:12]) if found else "无"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
