"""Extract Swift symbol names of the AulaF3009Manager module from the Mach-O
binary (ASCII string scan, no external deps)."""
import re
import sys

PATH = r"D:\Project\OpenALUA\research\f3009mac\AULA F3009 管理器.app\Contents\MacOS\AulaF3009Manager"


def ascii_strings(data: bytes, min_len=6):
    out = []
    cur = bytearray()
    for b in data:
        if 32 <= b <= 126:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= min_len:
        out.append(cur.decode("ascii"))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    data = open(PATH, "rb").read()
    strings = ascii_strings(data)
    syms = sorted({s for s in strings if s.startswith("_$s16AulaF3009Manager")})
    print(f"total strings: {len(strings)}, module symbols: {len(syms)}")
    print("=" * 100)
    for s in syms:
        # strip SwiftUI view body fluff: keep the head which names the type/func
        head = s[:220]
        print(head)
    print("=" * 100)
    # other interesting printable strings (UI text, formats)
    interesting = [s for s in strings
                   if not s.startswith("_$s") and not s.startswith("__T")
                   and re.search(r"(?i)report|0x|vid|pid|sleep|battery|effect|hid|cmd|slot|profile", s)]
    seen = set()
    for s in interesting:
        if s in seen:
            continue
        seen.add(s)
        if len(s) <= 300:
            print(repr(s))


if __name__ == "__main__":
    main()
