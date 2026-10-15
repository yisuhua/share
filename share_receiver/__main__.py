import argparse
import logging
import threading
from pathlib import Path

from .core import ReceiverServer, Settings


def main():
    parser = argparse.ArgumentParser(description='Share LAN receiver')
    parser.add_argument('--headless', action='store_true', help='Run receiver without desktop UI')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    settings = Settings(args.config)
    server = ReceiverServer((args.host, args.port), settings)
    if args.headless:
        logging.info('Listening on %s:%s; config: %s; destination: %s',
                     args.host, server.server_port, settings.config, settings.folder)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    from .desktop import Desktop
    import tkinter as tk
    root = tk.Tk()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        Desktop(root, settings, server)
        root.mainloop()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


if __name__ == '__main__':
    main()
