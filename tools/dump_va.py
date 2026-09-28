"""Dump the full disassembly of specific VA ranges of ShinetekTools.exe."""
import sys

import capstone
import pefile

EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"

RANGES = [
    ("write-reg fn B  (reg=0x20 writer #2)", 0x421B20, 0x421C60),
    ("write-reg fn A  (reg=index writer)", 0x421660, 0x421760),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pe = pefile.PE(EXE)
    text = next(s for s in pe.sections if b".text" in s.Name)
    base = pe.OPTIONAL_HEADER.ImageBase
    va0 = text.VirtualAddress + base
    code = text.get_data()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    all_insns = list(md.disasm(code, va0))
    data = open(EXE, "rb").read()
    print(f"total instructions in .text: {len(all_insns)}")
    for title, start, end in RANGES:
        print("=" * 110)
        print(f"### {title}  0x{start:x} .. 0x{end:x}")
        for ins in all_insns:
            if ins.address >= end:
                break
            if ins.address < start:
                continue
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
                                comment = f"   ; \"{s.decode('ascii')}\""
                except Exception:  # noqa: BLE001
                    pass
            print(f"0x{ins.address:x}: {ins.mnemonic:8s} {ins.op_str}{comment}")


if __name__ == "__main__":
    main()
