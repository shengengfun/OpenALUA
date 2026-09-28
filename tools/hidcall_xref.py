"""Static analysis of ShinetekTools.exe: locate calls to HID APIs through the
IAT and dump the preceding instructions to reveal report buffer construction.

READ-ONLY analysis of the binary; does not touch any device.
"""
import re
import sys

import capstone
import pefile

EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"
TARGET_FUNCS = {
    "HidD_SetFeature", "HidD_GetFeature", "HidD_SetOutputReport",
    "HidD_GetInputReport", "WriteFile", "ReadFile", "DeviceIoControl",
}


def collect_iat(pe, wanted):
    """Return {funcname: iat_slot_va}."""
    out = {}
    if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        return out
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in entry.imports:
            if imp.name and imp.name.decode(errors="replace") in wanted:
                out[imp.name.decode()] = imp.address
    return out


def is_64(pe):
    return pe.FILE_HEADER.Machine == 0x8664


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pe = pefile.PE(EXE)
    iat = collect_iat(pe, TARGET_FUNCS)
    print(f"machine=0x{pe.FILE_HEADER.Machine:04x} (64bit={is_64(pe)})")
    for k, v in sorted(iat.items()):
        print(f"  IAT {k:24s} = 0x{v:x}")

    text = None
    for s in pe.sections:
        if b".text" in s.Name:
            text = s
            break
    base = pe.OPTIONAL_HEADER.ImageBase
    va = text.VirtualAddress + base
    code = text.get_data()
    mode = capstone.CS_MODE_64 if is_64(pe) else capstone.CS_MODE_32
    md = capstone.Cs(capstone.CS_ARCH_X86, mode)
    md.detail = False

    insns = []
    for i in md.disasm(code, va):
        insns.append((i.address, i.mnemonic, i.op_str))
    print(f"disassembled {len(insns)} instructions")

    iat_by_va = {addr: name for name, addr in iat.items()}
    pat = re.compile(r"\[(0x[0-9a-f]+)\]")

    hits = []  # (idx, funcname)
    for idx, (addr, mn, op) in enumerate(insns):
        if mn not in ("call", "jmp"):
            continue
        m = pat.search(op)
        if not m:
            continue
        target = int(m.group(1), 16)
        if target in iat_by_va:
            hits.append((idx, iat_by_va[target]))
    print(f"call sites: {len(hits)}")

    WINDOW = 45
    for idx, name in hits:
        print("=" * 110)
        print(f">>> CALL {name}  @ 0x{insns[idx][0]:x}")
        start = max(0, idx - WINDOW)
        for j in range(start, min(len(insns), idx + 3)):
            a, mn, op = insns[j]
            mark = ">>" if j == idx else "  "
            print(f"{mark} 0x{a:x}: {mn:8s} {op}")


if __name__ == "__main__":
    main()
