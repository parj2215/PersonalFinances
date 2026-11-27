"""Native Ubuntu webview, using Flask."""
import threading
from werkzeug.serving import make_server

from personal_finances.app import app

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

def main():
    try:
        import webview
    except ImportError as error:
        raise SystemExit("Install desktop dependencies: pip install -r requirements.txt") from error

    GLib.set_prgname("personal-finances")
    
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    try:
        webview.create_window("Personal Finances", f"http://127.0.0.1:{server.server_port}", width=1280, height=850, min_size=(850, 600))
        webview.start(gui="gtk", icon="assets/icon.png")
    finally:
        server.shutdown()
        thread.join(timeout=5)

if __name__ == "__main__":
    main()
