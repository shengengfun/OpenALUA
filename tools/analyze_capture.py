"""Decode a capture_hid.py log into structured findings.

Usage:  python tools/analyze_capture.py <log> [--xml] [--frames]

Outputs:
  * every distinct 8-byte feature frame (07 ...) with a running count
  * every distinct 64-byte output-report prefix (05 xx ...) with a count
  * all 256-byte text blobs reassembled in order and split on `<?xml`
"""
import re
import sys
import collections

LINE = re.compile(r"^\[(\S+)\s*\]\s+(\S+)\s+len=\s*(\d+)\s+(.*)$")


def load(path):
    entries = []
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
            entries.append((tag, name, int(ln), raw))
    return entries


def hexs(b, n=None):
    b = b if n is None else b[:n]
    return " ".join(f"{x:02x}" for x in b)


def report_feature(entries):
    """8-byte 07 frames = the real control channel."""
    print("\n=== 8-byte feature frames (07 ...) ===")
    order = []
    counts = collections.Counter()
    last = None
    for tag, name, ln, raw in entries:
        if ln != 8 or raw[0] != 0x07:
            continue
        key = hexs(raw)
        counts[key] += 1
        if key != last:
            order.append((key, tag))
            last = key
    print(f"distinct: {len(counts)}")
    for key, tag in order:
        print(f"  {tag:6s} {key}")
    print("\n-- counts --")
    for key, c in counts.most_common():
        print(f"  {c:5d}x  {key}")
    return counts


def report_output(entries):
    """64-byte 05 frames: init sequence vs. LED payloads vs. XML chunks."""
    print("\n=== 64-byte output reports, prefix histogram ===")
    hist = collections.Counter()
    for tag, name, ln, raw in entries:
        if ln == 64:
            hist[hexs(raw, 8)] += 1
    for key, c in hist.most_common(40):
        print(f"  {c:5d}x  {key}")


def report_xml(entries):
    """Every 256-byte write that is not a 05-frame is a slice of a text blob."""
    print("\n=== 256-byte text blobs (macro / config XML) ===")
    buf = bytearray()

    def flush():
        nonlocal buf
        if not buf:
            return
        text = buf.decode("utf-8", errors="replace")
        buf = bytearray()
        chunks = re.split(r"(?=<\?xml)", text)
        for ch in chunks:
            ch = ch.strip()
            if not ch:
                continue
            print("-" * 70)
            print(ch)

    for tag, name, ln, raw in entries:
        if ln == 256:
            buf += raw
        else:
            flush()
    flush()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"d:\Project\OpenALUA\research\hid_capture.log"
    only = set(a for a in sys.argv[2:] if a.startswith("--"))
    entries = load(path)
    print(f"{len(entries)} entries from {path}")
    if not only or "--frames" in only:
        report_feature(entries)
        report_output(entries)
    if not only or "--xml" in only:
        report_xml(entries)


if __name__ == "__main__":
    main()
