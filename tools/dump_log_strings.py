"""Dump ASCII strings at specific VAs referenced by ShinetekTools logging calls,
plus all printf-like format strings in .rdata (they hint at command tracing)."""
import sys

import pefile

EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"
VAS = [0x6971E4, 0x696FDC, 0x696F8C, 0x69907C, 0x69908C, 0x696A44]


def cstr(data, off, limit=240):
    end = data.find(b"\x00", off)
    if end == -1 or end - off > limit:
        end = off + limit
    return data[off:end].decode("latin-1", errors="replace")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pe = pefile.PE(EXE)
    base = pe.OPTIONAL_HEADER.ImageBase

    print("=== strings at referenced VAs ===")
    for va in VAS:
        try:
            off = pe.get_offset_from_rva(va - base)
            data = open(EXE, "rb").read()
            print(f"0x{va:x}: {cstr(data, off)!r}")
        except Exception as e:  # noqa: BLE001
            print(f"0x{va:x}: ERR {e}")

    print("\n=== format-like strings in rdata ===")
    rdata = next((s for s in pe.sections if b".rdata" in s.Name), None)
    if rdata:
        blob = rdata.get_data()
        va0 = rdata.VirtualAddress + base
        cur = bytearray()
        start = 0
        for i in range(len(blob) + 1):
            b = blob[i] if i < len(blob) else 0
            if 32 <= b <= 126:
                if not cur:
                    start = i
                cur.append(b)
            else:
                if len(cur) >= 6:
                    s = cur.decode("ascii")
                    if "%" in s and any(t in s.lower() for t in
                                        ("02x", "%d", "%02", "%x", "02X", "04x")):
                        print(f"0x{va0 + start:x}: {s}")
                cur = bytearray()


if __name__ == "__main__":
    main()
