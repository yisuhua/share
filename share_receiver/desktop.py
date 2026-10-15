"""Desktop-only UI. Tk is kept on its owning thread; uploads run separately."""
from __future__ import annotations

import os
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import ReceiverServer, Settings


def local_addresses(port: int) -> str:
    addresses = {'127.0.0.1'}
    try:
        addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
        # UDP connect selects a route locally; it does not send a packet.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1', 9))
            addresses.add(sock.getsockname()[0])
    except OSError:
        pass
    return '\n'.join(f'http://{ip}:{port}' for ip in sorted(addresses))


class Desktop:
    def __init__(self, root: tk.Tk, settings: Settings, server: ReceiverServer):
        self.root, self.settings, self.server = root, settings, server
        self.panel = None
        self.unread = 0
        self.total = 0
        self.recent = []
        self.drag = None
        root.title('Share 接收球')
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.geometry(f'76x76+{max(0, root.winfo_screenwidth()-110)}+180')
        root.configure(bg='#f0f1f5')
        if sys.platform == 'win32':
            root.wm_attributes('-transparentcolor', '#f0f1f5')
        self.canvas = tk.Canvas(root, width=76, height=76, bg='#f0f1f5', highlightthickness=0)
        self.canvas.pack()
        self.circle = self.canvas.create_oval(5, 5, 71, 71, fill='#2459e0', outline='')
        self.caption = self.canvas.create_text(38, 38, text='Share', fill='white', font=('Segoe UI', 12, 'bold'))
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.move)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        menu = tk.Menu(root, tearoff=False)
        menu.add_command(label='接收记录与设置', command=self.show_panel)
        menu.add_command(label='打开接收文件夹', command=self.open_folder)
        menu.add_separator()
        menu.add_command(label='退出 Share', command=self.close)
        self.canvas.bind('<Button-3>', lambda event: menu.tk_popup(event.x_root, event.y_root))
        self.root.after(200, self.poll)
        self.show_panel()

    def press(self, event):
        self.drag = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y(), False)

    def move(self, event):
        if self.drag is None:
            return
        x, y, wx, wy, moved = self.drag
        dx, dy = event.x_root - x, event.y_root - y
        moved = moved or abs(dx) + abs(dy) > 6
        self.drag = (x, y, wx, wy, moved)
        if moved:
            nx = min(max(0, wx + dx), max(0, self.root.winfo_screenwidth() - 76))
            ny = min(max(0, wy + dy), max(0, self.root.winfo_screenheight() - 76))
            self.root.geometry(f'+{nx}+{ny}')

    def release(self, _event):
        if self.drag is not None and not self.drag[4]:
            self.show_panel()
        self.drag = None

    def show_panel(self):
        self.unread = 0
        self.paint()
        if self.panel is not None and self.panel.winfo_exists():
            self.panel.deiconify()
            self.panel.lift()
            return
        p = self.panel = tk.Toplevel(self.root)
        p.title('Share · 局域网接收')
        p.geometry('600x570')
        p.minsize(480, 470)
        p.protocol('WM_DELETE_WINDOW', p.withdraw)
        frame = ttk.Frame(p, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Share 接收器', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='接收服务正在运行 · 点击球查看文件，拖动球改变位置').pack(anchor='w', pady=(4, 15))
        ttk.Label(frame, text='连接地址（平板选择电脑 Wi-Fi 对应的地址）').pack(anchor='w')
        addresses = tk.Text(frame, height=3, font=('Consolas', 11))
        addresses.insert('1.0', local_addresses(self.server.server_port))
        addresses.configure(state='disabled')
        addresses.pack(fill='x', pady=5)
        ttk.Label(frame, text='配对密码（仅给受信任的设备；HTTP 仅适合可信局域网）').pack(anchor='w', pady=(8, 0))
        token = ttk.Entry(frame, font=('Consolas', 11), show='●')
        token.insert(0, self.settings.token)
        token.configure(state='readonly')
        token.pack(fill='x', pady=5)
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        ttk.Button(actions, text='显示 / 隐藏密码', command=lambda: token.configure(show='' if token.cget('show') else '●')).pack(side='left')
        ttk.Button(actions, text='复制密码', command=self.copy_token).pack(side='left', padx=8)
        ttk.Label(frame, text='默认接收目录').pack(anchor='w', pady=(16, 0))
        self.folder_text = tk.StringVar(value=str(self.settings.folder))
        ttk.Entry(frame, textvariable=self.folder_text, state='readonly').pack(fill='x', pady=5)
        folders = ttk.Frame(frame)
        folders.pack(fill='x')
        ttk.Button(folders, text='更改默认文件夹', command=self.choose_folder).pack(side='left')
        ttk.Button(folders, text='打开文件夹', command=self.open_folder).pack(side='left', padx=8)
        ttk.Label(frame, text='最近接收（最多显示 100 条；文件不会自动删除）').pack(anchor='w', pady=(16, 4))
        self.history = tk.Listbox(frame, height=6)
        self.history.pack(fill='both', expand=True)
        for line in self.recent:
            self.history.insert('end', line)
        ttk.Button(frame, text='退出并停止接收', command=self.close).pack(anchor='e', pady=(12, 0))

    def copy_token(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.settings.token)

    def choose_folder(self):
        selected = filedialog.askdirectory(parent=self.panel, initialdir=str(self.settings.folder))
        if not selected:
            return
        try:
            self.settings.set_folder(Path(selected))
            self.folder_text.set(str(self.settings.folder))
        except (OSError, ValueError) as error:
            messagebox.showerror('无法设置接收目录', str(error), parent=self.panel)

    def open_folder(self):
        try:
            if sys.platform == 'win32':
                os.startfile(str(self.settings.folder))
            else:
                subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(self.settings.folder)])
        except OSError as error:
            messagebox.showerror('无法打开目录', str(error))

    def paint(self):
        self.canvas.itemconfigure(self.circle, fill='#16845a' if self.unread else '#2459e0')
        self.canvas.itemconfigure(self.caption, text=f'+{self.unread}' if self.unread else 'Share')

    def poll(self):
        while True:
            try:
                event = self.settings.events.get_nowait()
            except queue.Empty:
                break
            self.total += 1
            visible = self.panel is not None and self.panel.winfo_exists() and self.panel.state() != 'withdrawn'
            if not visible:
                self.unread += 1
            line = f'{event["name"]}   ·   {event["bytes"]:,} bytes'
            self.recent.insert(0, line)
            self.recent = self.recent[:100]
            if self.panel is not None and self.panel.winfo_exists():
                self.history.insert(0, line)
                if self.history.size() > 100:
                    self.history.delete(100, 'end')
        self.paint()
        self.root.after(200, self.poll)

    def close(self):
        # Stop accepting new requests. Active uploads may need retry after exit.
        threading.Thread(target=self.server.shutdown, daemon=True).start()
        self.root.destroy()
