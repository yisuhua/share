# Share

面向华为平板 → Windows 电脑的局域网文件传输项目。

**当前状态：PARTIAL。电脑接收服务与悬浮球源代码已实现；鸿蒙跨应用悬浮球及直接拖入文件尚未完成，当前没有可安装的平板 HAP。** 不把网页按钮当成系统悬浮球。

## Windows 启动

安装带 Tk 的 Python 3.11 或更高版本后，双击 `start_windows.cmd`，或在项目目录运行：

```powershell
py -3 -m share_receiver
```

运行后出现悬浮球和设置面板。拖动球移动；点击球查看接收记录；右键球打开菜单或退出。设置中可修改默认接收文件夹，后续上传自动保存。默认是 `Downloads\Share`。收到文件后球显示未读数量。

接收服务默认监听 TCP 8765，仅在可信局域网使用；Windows 提示防火墙时，只允许所需的专用网络。不要给公网配置端口转发。配对密码只保存在本机设置中，勿提交仓库或发送给不信任的人。

当前尚无完整平板发送端，因此启动电脑接收器不等于已经能够从平板悬浮球发送。

## 开发测试

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q share_receiver
```

无界面接收：`py -3 -m share_receiver --headless`。

参见 [设计与能力边界](docs/DESIGN.md)、[协议](docs/PROTOCOL.md) 和 [续跑状态](docs/CHECKPOINT.md)。
