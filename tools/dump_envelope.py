"""Disassemble the three functions that build the 2.4 GHz envelope.

They all embed the magic BB AA 99 88 and then set the byte right after it,
which acts as a command discriminator:
    push 0x36 -> byte = 0xAA   (the lighting command we captured)
    push 0x3B -> byte = 0x00
    push 0x3A -> byte = <al>   (two variable bytes -> looks like a register op)

Usage: python tools/dump_envelope.py
"""
import sys

import capstone
import pefile

MAGIC = bytes.fromhex("bbaa9988")
DEFAULT_EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXE
    pe = pefile.PE(path, fast_load=True)
    raw = open(path, "rb").read()
    base = pe.OPTIONAL_HEADER.ImageBase

    text = next(s for s in pe.sections if s.Name.rstrip(b"\x00").startswith(b".text"))
    tdata = text.get_data()
    tva = base + text.VirtualAddress
    toff = text.PointerToRawData

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False

    sites = []
    s = 0
    while True:
        i = tdata.find(MAGIC, s)
        if i < 0:
            break
        sites.append(i)
        s = i + 1

    for i in sites:
        va = tva + i
        back = 0x90          # bytes of context before the magic
        fwd = 0x90
        start = max(0, i - back)
        blob = tdata[start:i + fwd]
        print("=" * 78)
        print(f"site @ va=0x{va:08x}  (file 0x{toff + i:06x})   "
              f"前 {i - start} 字节上下文")
        print("=" * 78)
        for ins in md.disasm(blob, tva + start):
            mark = "  <<< 魔数" if ins.address <= va < ins.address + ins.size else ""
            print(f"  0x{ins.address:08x}  {ins.mnemonic:6s} {ins.op_str}{mark}")
        print()


if __name__ == "__main__":
    main()
