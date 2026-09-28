"""Decode a 2.4 GHz capture: the dongle has no feature reports, everything goes
out as 65-byte output reports with an envelope.

Usage: python tools/analyze_24g.py research/capture_24g.log
"""
import re
import sys
import collections

LINE = re.compile(r"^\[(\S+)\s*\]\s+(\S+)\s+len=\s*(\d+)\s+(.*)$")

MAGIC = bytes.fromhex("bbaa9988aa")


def load(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = LINE.match(line.strip())
            if not m:
                continue
            tag, name, ln, data = m.groups()
            try:
                raw = bytes(int(b, 16) for b in data.split())
            except ValueError:
                continue
            out.append((tag, name, int(ln), raw))
    return out


def hexs(b, n=None):
    b = b if n is None else b[:n]
    return " ".join(f"{x:02x}" for x in b)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = sys.argv[1] if len(sys.argv) > 1 else r"research/capture_24g.log"
    entries = load(path)
    print(f"{len(entries)} entries from {path}\n")

    print("=== timeline ===")
    for tag, name, ln, raw in entries:
        if ln >= 512:
            head = raw[:12]
            if MAGIC in raw[:8]:
                print(f"{tag:6s} len={ln:5d}  65B 信封: {hexs(head, 12)} …")
            else:
                txt = raw[:40].decode("utf-8", errors="replace").replace("\n", "\\n")
                print(f"{tag:6s} len={ln:5d}  文本: {txt}")
        elif ln == 65:
            kind = "信封" if raw[1:6] == MAGIC else "裸 65B"
            print(f"{tag:6s} len=  65  {kind}: {hexs(raw, 16)}")
        else:
            print(f"{tag:6s} len={ln:5d}  {hexs(raw)}")

    print("\n=== 65 字节报告去重 ===")
    hist = collections.Counter(hexs(r) for _t, _n, ln, r in entries if ln == 65)
    for k, c in hist.most_common():
        print(f"  {c:4d}x  {k}")

    print("\n=== 信封头部统计 (payload 起始 offset=7) ===")
    hist2 = collections.Counter()
    for _t, _n, ln, r in entries:
        if ln == 65 and r[1:6] == MAGIC:
            hist2[hexs(r[6:14])] += 1
    for k, c in hist2.most_common(40):
        print(f"  {c:4d}x  {k}")


if __name__ == "__main__":
    main()
