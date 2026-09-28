"""Disassemble an exact VA range of ShinetekTools.exe.

Start addresses MUST be real function entries (we pass `push ebp` prologues)
so instruction alignment is correct.
"""
import sys

import capstone
import pefile

EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"

RANGES = [
    ("0x20 writer #2  (fn @0x421b20)", 0x421B20, 0x421C60),
    ("0x20 writer #1  (fn @0x421620)", 0x421620, 0x421720),
    ("index writer    (fn @0x4214a0)", 0x4214A0, 0x4215A0),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pe = pefile.PE(EXE)
    text = next(s for s in pe.sections if b".text" in s.Name)
    base = pe.OPTIONAL_HEADER.ImageBase
    va0 = text.VirtualAddress + base
    data = open(EXE, "rb").read()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

    for title, start, end in RANGES:
        print("=" * 110)
        print(f"### {title}")
        off = start - va0
        seg = data[pe.get_offset_from_rva(start - base): pe.get_offset_from_rva(end - base)]
        for ins in md.disasm(seg, start):
            comment = ""
            if ins.mnemonic in ("push", "mov", "cmp", "lea") and "0x" in ins.op_str:
                try:
                    target = int(ins.op_str.split(",")[-1].strip(), 16)
                    if base <= target < base + pe.OPTIONAL_HEADER.SizeOfImage:
                        foff = pe.get_offset_from_rva(target - base)
                        end_b = data.find(b"\x00", foff)
                        if 0 <= end_b - foff <= 64:
                            s = data[foff:end_b]
                            if all(32 <= c < 127 for c in s) and len(s) >= 3:
                                comment = f'   ; "{s.decode("ascii")}"'
                except Exception:  # noqa: BLE001
                    pass
            print(f"0x{ins.address:x}: {ins.mnemonic:8s} {ins.op_str}{comment}")


if __name__ == "__main__":
    main()
