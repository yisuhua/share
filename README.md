# Share

面向华为平板 → Windows 电脑的局域网文件传输项目。

**当前状态：PARTIAL。电脑接收服务与悬浮球已通过 Windows 范围内验证；鸿蒙原生客户端源码已加入，但原生编译、签名和真机运行 NOT RUN，当前没有可安装的平板 HAP。** 不把上传页拖入功能当作系统球本体的文件拖入能力。

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
py -3 tests/windows_smoke.py
py -3 tests/curl_interop.py
```

无界面接收：`py -3 -m share_receiver --headless`。

本轮已在 Windows Python 3.13.14 通过 16 项接收测试、Tk 状态/生命周期 smoke check，以及真实 curl 的空文件和 2,097,155 字节 multipart 上传。平板真实跨应用悬浮、拖入文件和双端联调仍未执行。

## 平板原生源码

[`harmonyos/`](harmonyos/README.md) 包含 ArkUI 上传页、文件/图片选择、连接配置持久化、分段 SHA-256 校验、NetworkKit 文件上传和系统闪控球入口。此部分为 **PROPOSED / 原生未验证源码**；在 DevEco 中完成真实编译与签名后才能进入设备验收。

纯协议逻辑可使用 Node 24 执行：`node --test tests/client_contract.test.mjs`。此测试不调用鸿蒙 API，不代表客户端可编译或安装。

参见 [设计与能力边界](docs/DESIGN.md)、[协议](docs/PROTOCOL.md) 和 [续跑状态](docs/CHECKPOINT.md)。
