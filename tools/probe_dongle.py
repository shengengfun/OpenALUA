"""Probe the F3009 2.4 GHz dongle (1A2C:7FFF) for a usable vendor channel.

The dongle exposes two vendor collections, so the "2.4G has no feature report"
assumption was wrong. This script only *reads* unless --write is given.

Usage:
    python tools/probe_dongle.py            # read-only
    python tools/probe_dongle.py --write    # also try to set 常亮 at full brightness
"""
import sys
import time

import hid

VID = 0x1A2C
PID = 0x7FFF
VENDOR_PAGE = 0xFF01


def vendor_collections():
    out = []
    for d in hid.enumerate(VID, PID):
        if d.get("usage_page") == VENDOR_PAGE:
            out.append(d)
    return out


def show_caps(path):
    """Ask Windows for the preparsed caps of this collection."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None
    return None  # optional; hidapi already tells us enough


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    do_write = "--write" in sys.argv

    cols = vendor_collections()
    if not cols:
        print("没有找到厂商集合 —— 确认键盘在 2.4G 模式且接收器已插好")
        return 1

    print(f"找到 {len(cols)} 个厂商集合（0x{VENDOR_PAGE:04X}）\n")
    for c in cols:
        iface = c.get("interface_number")
        print("=" * 72)
        print(f"interface {iface}   usage_page=0x{c['usage_page']:04X} usage=0x{c['usage']:04X}")
        print(f"path: {c['path'].decode()}")

        dev = hid.device()
        try:
            dev.open_path(c["path"])
        except Exception as e:
            print(f"  打开失败: {e}\n")
            continue
        try:
            prod = dev.get_product_string()
            print(f"  product={prod!r}")

            # 1) plain GetFeature(7)
            try:
                data = dev.get_feature_report(0x07, 8)
                print(f"  GetFeature(7) 直读 -> {len(data)} 字节: " + " ".join(f"{b:02x}" for b in data))
            except Exception as e:
                print(f"  GetFeature(7) 直读失败: {e}")

            # 2) 官方读路径: 先 SetFeature(07 F1 ...) 再 GetFeature(7)
            try:
                dev.send_feature_report(bytes([0x07, 0xF1, 0, 0, 0, 0, 0, 0]))
                time.sleep(0.12)
                data = dev.get_feature_report(0x07, 8)
                print(f"  07 F1 读路径 -> {len(data)} 字节: " + " ".join(f"{b:02x}" for b in data))
            except Exception as e:
                print(f"  07 F1 读路径失败: {e}")

            # 3) 写测试（默认不做）
            if do_write:
                try:
                    dev.send_feature_report(bytes([0x07, 0xFF, 0xFF, 0x00, 0x05, 0x00, 0x00, 0x00]))
                    print("  已发送 07 FF FF 00 05 00 00 00（常亮 / 最亮）—— 看键盘有没有反应")
                except Exception as e:
                    print(f"  写失败: {e}")
        finally:
            dev.close()
        print()

    if not do_write:
        print("（只读模式。要试写灯光请加 --write）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
