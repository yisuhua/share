"""Tk update controls; network and staging never run on the UI thread."""
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk

from .updates import check_latest, download_release, stage_package, read_current, validate_installed
from .version import VERSION


class UpdateWindow:
    def __init__(self, desktop):
        self.desktop = desktop
        self.window = tk.Toplevel(desktop.root)
        self.window.title('Share · 应用内更新')
        self.window.geometry('480x250')
        self.window.protocol('WM_DELETE_WINDOW', self.window.withdraw)
        self.events = queue.Queue()
        self.release = None
        self.staged = False
        self.install = None
        candidate = os.environ.get('SHARE_INSTALL_ROOT')
        if candidate:
            root = Path(candidate).resolve()
            if ((root / 'launcher.pyw').is_file()
                    and Path(__file__).resolve().parent.parent == root / 'releases' / VERSION
                    and read_current(root).get('version') == VERSION):
                self.install = root
        self.status = tk.StringVar(value=f'当前版本 {VERSION}。点击检查更新。')
        ttk.Label(self.window, textvariable=self.status, wraplength=440).pack(fill='x', padx=20, pady=20)
        self.check = ttk.Button(self.window, text='检查更新', command=self.check_now)
        self.check.pack(pady=4)
        self.action = ttk.Button(self.window, text='下载更新', command=self.download, state='disabled')
        self.action.pack(pady=4)
        if self.install is None:
            ttk.Label(self.window, text='源码运行模式：先运行 install_windows.cmd 安装一次。').pack(pady=10)
        self.window.after(100, self.poll)

    def run(self, operation):
        self.check.configure(state='disabled')
        self.action.configure(state='disabled')
        def worker():
            try: self.events.put(('ok', operation()))
            except Exception as error: self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def check_now(self):
        self.status.set('正在检查 GitHub 正式版本…')
        def check():
            release = check_latest(VERSION)
            if release and self.install and (self.install / 'releases' / release.version).exists():
                validate_installed(self.install, release.version)
                return ('staged', release)
            return ('release', release)
        self.run(check)

    def download(self):
        if self.staged:
            self.restart()
            return
        release = self.release
        if release is None or self.install is None: return
        self.status.set('正在下载并校验更新包；文件接收继续运行…')
        def prepare():
            with tempfile.TemporaryDirectory(prefix='share-update-') as temp:
                package = Path(temp) / 'update.zip'
                download_release(release, package)
                stage_package(package, self.install, release.version)
            return ('staged', release)
        self.run(prepare)

    def restart(self):
        if not self.desktop.server.try_pause_idle():
            self.status.set('正在接收文件，请接收完成后再点“重启更新”。')
            return
        try:
            subprocess.Popen([sys.executable, str(self.install / 'launcher.pyw'),
                              '--wait-pid', str(os.getpid()), '--target', self.release.version,
                              '--', '--host', str(self.desktop.server.server_address[0]),
                              '--port', str(self.desktop.server.server_port),
                              '--config', str(self.desktop.settings.config.resolve())], cwd=self.install)
        except OSError as error:
            self.desktop.server.resume()
            self.status.set(f'无法启动更新：{error}；当前版本继续运行。')
            return
        self.desktop.close()

    def poll(self):
        try:
            while True:
                kind, result = self.events.get_nowait()
                self.check.configure(state='normal')
                if kind == 'error':
                    self.status.set('更新失败：' + result)
                    self.action.configure(state='normal' if self.release and self.install else 'disabled')
                    continue
                step, release = result
                self.release = release
                if step == 'release':
                    self.staged = False
                    self.status.set(f'发现新版本 {release.version}。下载校验后可重启更新。' if release else '当前已是最新的正式版本。')
                    self.action.configure(text='下载更新', state='normal' if release and self.install else 'disabled')
                else:
                    self.staged = True
                    self.status.set(f'{release.version} 已校验并暂存。重启后生效，接收目录与密码保留。')
                    self.check.configure(state='disabled')
                    self.action.configure(text='重启更新', state='normal')
        except queue.Empty:
            pass
        if self.window.winfo_exists(): self.window.after(100, self.poll)
