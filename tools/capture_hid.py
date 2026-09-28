"""Capture the real HID protocol of ShinetekTools.exe by hooking Windows HID APIs
with frida (no driver install needed).

Spawns the official tool, hooks HidD_SetFeature / HidD_GetFeature /
HidD_SetOutputReport / WriteFile, and prints every buffer.
"""
import sys
import time

import frida

EXE = r"C:\Program Files (x86)\AULA\F3001 三模机械键盘\ShinetekTools.exe"

JS = r"""
function hook(mod, name, tag, lenArg) {
  var addr = null;
  try { addr = Module.getExportByName(mod, name); } catch (e) {
    try { addr = Module.getGlobalExportByName(name); } catch (e2) { return; }
  }
  if (!addr) return;
  Interceptor.attach(addr, {
    onEnter: function (args) {
      try {
        var total = args[lenArg].toInt32();
        if (total <= 0) return;
        var len = total > 4096 ? 4096 : total;
        var p = args[1];
        var out = [];
        for (var i = 0; i < len; i++) {
          var b = p.add(i).readU8();
          out.push(('0' + b.toString(16)).slice(-2));
        }
        send({ tag: tag, name: name, len: total, read: len, data: out.join(' ') });
      } catch (e) { send({ err: tag + ': ' + String(e) }); }
    }
  });
  send({ hooked: tag + ':' + name });
}

hook('hid.dll', 'HidD_SetFeature', 'SET', 2);
hook('hid.dll', 'HidD_GetFeature', 'GET', 2);
hook('hid.dll', 'HidD_SetOutputReport', 'SETOUT', 2);
hook('kernel32.dll', 'WriteFile', 'WRITE', 2);
send({ ready: true });
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    log_path = sys.argv[1] if len(sys.argv) > 1 else r"d:\Project\OpenALUA\research\hid_capture.log"
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    log = open(log_path, "w", encoding="utf-8")

    def emit(line):
        print(line)
        log.write(line + "\n")
        log.flush()

    pid = frida.spawn(EXE)
    emit(f"[frida] spawned pid={pid}")
    session = frida.attach(pid)
    script = session.create_script(JS)

    def on_message(msg, data):
        if msg["type"] == "send":
            p = msg["payload"]
            if p.get("ready"):
                emit("[frida] hook ready")
            elif "hooked" in p:
                emit(f"[frida] hooked {p['hooked']}")
            elif "err" in p:
                emit(f"[err] {p['err']}")
            else:
                emit(f"[{p.get('tag'):6s}] {p.get('name'):22s} len={p.get('len'):3d}  {p.get('data')}")
        else:
            emit(f"[frida-msg] {msg}")

    script.on("message", on_message)
    script.load()
    frida.resume(pid)
    emit(f"=== capturing {duration:.0f} s — please operate the AULA tool now ===")
    time.sleep(duration)
    emit("=== capture window done ===")
    log.close()


if __name__ == "__main__":
    main()
