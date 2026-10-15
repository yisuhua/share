"""Run explicitly on Windows: py -3 tests/windows_smoke.py.

Creates temporary loopback-only server, briefly opens UI, then stops everything.
This verifies UI state/lifecycle, not visual appearance or tablet interoperability.
"""
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from share_receiver.core import ReceiverServer, Settings
from share_receiver.desktop import Desktop


def main():
    if sys.platform != 'win32':
        raise RuntimeError('This smoke check must run on Windows')
    with tempfile.TemporaryDirectory(prefix='Share-gui-check-') as tmp:
        base = Path(tmp)
        settings = Settings(base / 'settings.json', base / 'received')
        server = ReceiverServer(('127.0.0.1', 0), settings)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        root = tk.Tk()
        try:
            app = Desktop(root, settings, server)
            root.update()
            assert root.attributes('-topmost')
            assert app.panel.winfo_exists()
            settings.notify({'name': 'test.png', 'bytes': 3})
            app.poll()
            assert app.history.size() == 1
            app.panel.withdraw()
            root.update()
            settings.notify({'name': 'second.png', 'bytes': 3})
            app.poll()
            assert app.unread == 1
            settings.set_folder(base / 'new-destination')
            assert settings.folder == base / 'new-destination'
            app.show_panel()
            root.update()
            assert app.unread == 0
            app.show_updates()
            root.update()
            update = app.update_window
            assert update.window.winfo_exists()
            assert update.install is None
            update.events.put(('error', 'simulated offline'))
            update.poll()
            assert 'simulated offline' in update.status.get()
            update.window.withdraw()
            app.show_updates()
            root.update()
            assert update.window.state() == 'normal'
        finally:
            root.destroy()
            server.shutdown()
            server.server_close()
            worker.join(2)
    print('WINDOWS_TK_SMOKE_PASS', sys.version)


if __name__ == '__main__':
    main()
