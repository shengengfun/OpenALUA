"""Walk one level up from the HID wrapper functions in ShinetekTools.exe:
find every `call <wrapper>` site and dump the preceding instructions where
the report payload is usually assembled.

READ-ONLY static analysis.
"""
import re
import sys

import capstone
import pefile

EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"
# wrapper call sites discovered earlier (HidD_* via IAT)
WRAPPER_SITES = {
    "SetFeature@0x404d2c": 0x404D2C,
    "GetFeature@0x404f77": 0x404F77,
    "SetFeature@0x405089": 0x405089,
    "SetFeature@0x40327f": 0x40327F,
    "GetFeature@0x40325f": 0x40325F,
    "WriteFile@0x403319": 0x403319,
    "WriteFile@0x403406": 0x403406,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pe = pefile.PE(EXE)
    text = next(s for s in pe.sections if b".text" in s.Name)
    base = pe.OPTIONAL_HEADER.ImageBase
    va = text.VirtualAddress + base
    code = text.get_data()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    insns = [(i.address, i.mnemonic, i.op_str) for i in md.disasm(code, va)]
    addr2idx = {a: i for i, (a, _, _) in enumerate(insns)}

    def func_start(call_idx):
        """Heuristic: first instruction after the previous `ret`."""
        for j in range(call_idx, -1, -1):
            if insns[j][1] == "ret":
                return insns[j + 1][0] if j + 1 < len(insns) else None
        return None

    # identify wrapper function starts
    wrappers = {}
    for label, addr in WRAPPER_SITES.items():
        idx = addr2idx.get(addr)
        if idx is None:
            print(f"!! site {label} not found")
            continue
        start = func_start(idx)
        wrappers[label] = start
        print(f"wrapper {label}: site=0x{addr:x} start~0x{start:x}" if start else f"wrapper {label}: start unknown")

    # locate true wrapper entries: search backwards from each IAT call site for
    # the classic prologue `push ebp; mov ebp, esp` (55 8B EC)
    raw = text.get_data()
    entries = {}
    for label, addr in WRAPPER_SITES.items():
        off = addr - va
        entry = None
        for k in range(off, max(-1, off - 0x600), -1):
            if raw[k] == 0x55 and raw[k + 1] == 0x8B and raw[k + 2] == 0xEC:
                entry = va + k
                break
        entries[label] = entry
        print(f"wrapper {label}: site=0x{addr:x} entry=0x{entry:x}" if entry else f"wrapper {label}: entry NOT FOUND")

    # exact raw E8 scan to wrapper entries
    print("\ncallers:")
    entry_map = {}
    for label, e in entries.items():
        if e and e not in entry_map:
            entry_map[e] = label
    WINDOW = 60
    found = []
    for off in range(0, len(raw) - 5):
        if raw[off] != 0xE8:
            continue
        rel = int.from_bytes(raw[off + 1:off + 5], "little", signed=True)
        tgt = va + off + 5 + rel
        if tgt in entry_map:
            found.append((va + off, entry_map[tgt]))
    found.sort()
    for a, wname in found:
        print(f"  0x{a:x} -> {wname}")

    WINDOW = 70
    for call_addr, wname in found:
        idx = addr2idx.get(call_addr)
        print("=" * 110)
        print(f">>> CALLER of {wname} @ 0x{call_addr:x}")
        if idx is None:
            start_off = max(0, call_addr - va - WINDOW * 4)
            seg = raw[start_off:call_addr - va + 5]
            for ins in capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(seg, va + start_off):
                mark = ">>" if ins.address == call_addr else "  "
                print(f"{mark} 0x{ins.address:x}: {ins.mnemonic:8s} {ins.op_str}")
            continue
        start = max(0, idx - WINDOW)
        for j in range(start, min(len(insns), idx + 4)):
            a, mn, op = insns[j]
            mark = ">>" if j == idx else "  "
            print(f"{mark} 0x{a:x}: {mn:8s} {op}")


if __name__ == "__main__":
    main()
