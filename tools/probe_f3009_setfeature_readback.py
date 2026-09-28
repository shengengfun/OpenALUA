"""Verify the hypothesis that the read path is:
   HidD_SetFeature(handle, buf=07 F1 idx 00 00 00 00 00) -> vhidflt fills buf with the answer.

Uses the raw Windows HID API so we can inspect the *same* buffer after the call
(hidapi's send_feature_report does not expose this).

READ-ONLY semantics: only the driver's own read command (0xF1) is sent.
"""
import ctypes
import sys
import time
from ctypes import wintypes

hid_dll = ctypes.WinDLL("hid.dll")
kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

THROTTLE = 0.11


def open_path(path: str):
    h = kernel32.CreateFileW(
        path,
        0x40000000 | 0x80000000,  # GENERIC_WRITE | GENERIC_READ
        0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
        None,
        3,       # OPEN_EXISTING
        0,       # no FILE_FLAG_OVERLAPPED -> blocking
        None,
    )
    if h in (-1, None, 0xFFFFFFFFFFFFFFFF):
        raise OSError(f"CreateFile failed: {ctypes.get_last_error()}")
    return h


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import hid as hidapi
    devs = [d for d in hidapi.enumerate(0x1A2C, 0x7F05)
            if d["usage_page"] == 0xFF01 and d["usage"] == 0x0001]
    if not devs:
        print("Col07 not found")
        return
    path = devs[0]["path"].decode("utf-8")
    print(f"path={path}")

    handle = open_path(path)
    try:
        buf = (ctypes.c_ubyte * 8)()
        print("\n--- read command 07 F1 <idx> ---")
        for idx in list(range(0, 20)) + [0x20, 0x30, 0x40, 0x50, 0x80, 0xFF]:
            for i in range(8):
                buf[i] = 0
            buf[0], buf[1], buf[2] = 0x07, 0xF1, idx
            ok = hid_dll.HidD_SetFeature(handle, ctypes.byref(buf), 8)
            after = bytes(buf)
            print(f"idx=0x{idx:02x} ok={bool(ok)} -> {after.hex(' ')}")
            time.sleep(THROTTLE)

        print("\n--- baseline GetFeature(7) ---")
        g = (ctypes.c_ubyte * 8)()
        g[0] = 7
        ok = hid_dll.HidD_GetFeature(handle, ctypes.byref(g), 8)
        print(f"ok={bool(ok)} -> {bytes(g).hex(' ')}")
    finally:
        kernel32.CloseHandle(handle)


if __name__ == "__main__":
    main()
