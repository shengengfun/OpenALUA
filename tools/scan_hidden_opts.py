"""Hunt for hidden firmware options (sleep timer, polling rate, debounce) in the
official AULA tool: dump its config files and grep the binaries for keywords.

Usage: python tools/scan_hidden_opts.py "C:\\Program Files (x86)\\AULA"
"""
import os
import re
import sys

KEYWORDS = [
    "sleep", "sleep_time", "sleeptime", "休眠", "睡眠", "省电", "lowpower",
    "low_power", "power_save", "powersave", "idle",
    "poll", "polling", "回报率", "回报", "reportrate", "report_rate", "hz",
    "debounce", "去抖", "防抖", "respondtime", "key_respondtime", "response_time",
    "timer", "timeout", "autosleep", "auto_sleep",
    "battery", "电量", "capacity",
    "macros", "macrosave", "keymap", "remap", "改键", "宏",
    "ledeffect", "setting", "config",
]

TEXT_EXT = {".xml", ".ini", ".json", ".txt", ".cfg", ".conf", ".lua", ".js"}
BIN_EXT = {".exe", ".dll", ".sys", ".ocx"}

PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")
UTF16 = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")


def scan_text_blob(blob, label, hits):
    """Find keywords in an ascii / utf-16 blob, print context."""
    for m in PRINTABLE.finditer(blob):
        s = m.group().decode("latin-1")
        low = s.lower()
        for kw in KEYWORDS:
            if kw in low:
                hits.setdefault(kw, []).append((label, s.strip()[:160]))
                break
    for m in UTF16.finditer(blob):
        try:
            s = m.group().decode("utf-16-le")
        except UnicodeDecodeError:
            continue
        low = s.lower()
        for kw in KEYWORDS:
            if kw in low:
                hits.setdefault(kw, []).append((label + " [u16]", s.strip()[:160]))
                break


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files (x86)\AULA"
    hits = {}
    print(f"### walking {root}\n")

    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            full = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root)

            if ext in TEXT_EXT and size < 400_000:
                try:
                    data = open(full, "rb").read()
                except OSError:
                    continue
                text = data.decode("utf-8", errors="replace")
                if "<?xml" in text or ext == ".ini" or ext == ".json":
                    print("=" * 72)
                    print(f"--- {rel}  ({size} B) ---")
                    body = text.strip()
                    print(body[:2500] if len(body) <= 2500 else body[:2500] + "\n...[截断]")
                scan_text_blob(data, rel, hits)
            elif ext in BIN_EXT and size < 40_000_000:
                try:
                    data = open(full, "rb").read()
                except OSError:
                    continue
                print(f"[scan] {rel} ({size} B)")
                scan_text_blob(data, rel, hits)

    print("\n" + "=" * 72)
    print("### keyword hits")
    for kw in KEYWORDS:
        got = hits.get(kw)
        if not got:
            continue
        print(f"\n--- {kw}  ({len(got)}) ---")
        seen = set()
        for label, ctx in got[:24]:
            key = (label, ctx)
            if key in seen:
                continue
            seen.add(key)
            print(f"  [{label}] {ctx}")


if __name__ == "__main__":
    main()
