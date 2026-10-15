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

## 应用内更新

电脑端首次解压 `Share-Windows-Setup-0.1.0.zip` 后，双击 `install_windows.cmd`，安装到当前用户目录。仍需已安装带 Tk 的 Python 3.11+；此包不是独立 EXE。安装后从开始菜单打开 Share，在接收面板或球的右键菜单选择“检查应用更新”。源码启动只允许检查，不会覆盖工作区。

发现正式版本后，点击“下载更新”。应用从 `yisuhua/share` 的 GitHub Releases 下载固定名称的更新包，校验 SHA-256 并暂存。点击“重启更新”前必须接收空闲；新版本报告服务与界面已就绪后完成启动。默认目录、配对密码和已接收文件保留。损坏包不切换，启动失败会尝试旧版本；重复打开不会触发版本切换。程序运行期间的后续崩溃不由启动器监控。

旧版本保存在 `%LOCALAPPDATA%\Share\program\releases`。需要手动回退时，退出 Share 后执行：

```powershell
py -3 "$env:LOCALAPPDATA\Share\program\launcher.pyw" --rollback
```

开发者修改 `share_receiver/version.py` 后运行 `py -3 tools/package_windows.py`，生成首次安装包及 `Share-Windows-<版本>.zip` 更新资产。正式 GitHub Release 标签必须为 `v<版本>`，上传同版本更新 ZIP，且 GitHub 资产信息含 SHA-256 digest；运行时和依赖变更不适用于当前仅更新 Python 程序的格式。本轮不发布 Release，线上检查/下载整链路尚未验收。

鸿蒙上传页已加入“检查应用更新”入口，使用 AppGalleryKit。当前未上架的开发版本显示更新不可用；待同包名、同签名正式版本上架并完成真机验证后启用。此入口没有改变当前无可安装 HAP 的状态。
