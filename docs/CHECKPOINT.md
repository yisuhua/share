# Working checkpoint

Project: yisuhua/share
Branch: codex/share-floating-receiver
Date: 2026-10-15
Overall: PARTIAL
Latest Valid (完整双端): 无

已实现电脑接收 API、Tk 悬浮球、默认目录持久化和接收记录。首阶段当前环境 Python 3.12.14，9 项真实 HTTP/磁盘测试通过；compileall 和 CLI help 通过。

Windows 实机验证：Python 3.13.14，9/9 HTTP/磁盘测试通过；Tk 实际创建置顶球和面板，接收记录更新、隐藏面板后未读计数、再次打开清零、目录切换、退出清理均通过。进程退出码 0。测试仅监听回环地址，已停止；未常驻部署、未修改防火墙。
Windows 验证工作目录：C:\Users\Lenovo\AppData\Local\Temp\Share-verify-20261015-cg29sh3m。
视觉效果、真实触摸拖动、跨设备网络：NOT RUN，不由上述 smoke test 推导为通过。
真实平板跨应用球、文件拖入、上传联调：NOT RUN。
DevEco 编译/签名与权限验证：NOT RUN。
当前可执行环境未发现 hdc/hvigorw 命令，也未在已检查的常见 Huawei SDK/DevEco 目录发现安装；不能据此断言用户电脑完全没有其他安装位置。未连接平板原生调试设备、未取得应用签名/受控权限验证证据。平板验收当前 BLOCKED。

已发现并修复：中断上传时响应早于清理临时文件；改为关闭文件并清理后返回错误，测试通过。

续跑：先按 DESIGN 的平板能力门禁验证，不改变“必须跨应用悬浮”的已确认条件。若未获取原生签名环境/权限/可用文件拖入 API，保留 BLOCKED，不宣称完整目标 PASS。

提交方式：本地 git push 因缺少 HTTPS 凭据失败；改用已授权 GitHub connector 创建仓库文件/分支。不得把本地 commit SHA 当成远程 commit SHA。

## 本轮续跑：原生源码与表单传输兼容

- 接收器增加 /v1/form-files 单文件流式 multipart 入口；raw /v1/files 和已有认证/校验/保存语义不变。
- 新增7项表单测试，16/16 HTTP/磁盘测试在当前环境及 Windows Python 3.13.14 上通过。
- 真实 curl multipart：空文件及2,097,155字节文件在当前环境和 Windows 上通过，独立核对原文件字节与回执SHA-256。
- Windows Tk smoke check 再次通过，所有测试进程退出码0；无常驻部署、无防火墙改动。
- Windows 本轮测试路径：C:\Users\Lenovo\AppData\Local\Temp\Share-native-wire-20261015-1x4vrvig。
- harmonyos/ 原生源码包含系统球、图片/文件选择、上传页拖入适配、流式文件表单上传、缓存清理与回执确认；状态 PROPOSED / 原生运行 NOT RUN。
- Node 24上3项纯协议测试通过；11个JSON配置和SVG XML可解析；7个非ArkUI源码文件通过Node TypeScript语法检查。以上不检查ArkTS特有规则，不包含Index.ets的ArkUI语法，不是原生编译。
- 重新检查Windows卸载注册表、常见目录与SDK环境变量，仍未定位DevEco/SDK/hdc；winget精确查询 Huawei.DevEcoStudio 返回No package found。未安装新开发工具，也未连接平板调试会话。

仍阻塞：DevEco/API20工具链的真实构建；用户账户/调试设备签名；USE_FLOAT_BALL实际授权；系统球本体文件drop能力。下一次从这些门禁继续，不重做已验证的接收层。

独立代码审查发现并修正：异步读取旧配置可能覆盖当前目标电脑；现已在读取期间禁用输入/动作，并对每次操作固定连接快照，预检查、持久化和整个批次使用同一地址/密码。失败上传的缓存清理警告原本会被主错误覆盖，现已合并到最终错误中。临时目录改用实际创建成功才返回的mkdtemp。审查者已针对修改回看，未发现剩余具体缺陷；此结论仅为源代码审查，不是原生运行验证。

验收清单：TABLET_ACCEPTANCE.md；API来源：API_SOURCES.md；独立证据记录：verification/2026-10-15-native-stage.md。

## 本轮续跑：应用内更新

用户已选择应用内更新。电脑端新增首次用户级安装、稳定启动器、GitHub 正式版查询、SHA-256 下载校验、严格 ZIP/每文件校验、版本暂存、空闲门禁、重启就绪握手和旧版本回退；保留配置、配对密码与接收文件。单实例 OS 文件锁避免重复打开误回退。源码模式只检查，不更新工作区。首次安装与更新 ZIP 可用 tools/package_windows.py 重建，仍依赖 Python 3.11+，不是独立 EXE。

本地 Python 34/34、Node 纯协议3/3、compileall、diff --check 通过。Windows Python 3.13.14 最终34/34通过，managed安装/更新UI smoke通过；同轮 Tk smoke、真实curl 0及2,097,155字节通过。Windows路径：C:\Users\Lenovo\AppData\Local\Temp\Share-update-verified-20261015-1l6ih2i3。详见verification/2026-10-15-update-stage.md。

独立审查的问题已修复并回归：普通启动失败不回退；坏版导入阻断回退；固定5秒存活误判就绪；相对配置路径漂移；重复启动误回退；中文快捷入口编码；小请求体拒绝引发Windows TCP reset。补读小请求体采用绝对250ms截止时间/read1，避免逐字节慢发无限延长。

鸿蒙加入AppGalleryKit官方更新入口，但STORE_RELEASED=false；未上架开发版本明确提示不可更新。此处SDK编译、枚举/syscap核验、签名、应用市场更新真机仍NOT RUN。GitHub Release真实发布/线上升级整链路NOT RUN；没有发布Release、合并PR、修改防火墙、安装到用户正式目录或写入开始菜单。

下一步：为原生端取得DevEco/API20、签名和真机验证环境；仍需验证系统球直接文件drop及USE_FLOAT_BALL授权。已验证的电脑更新层不等于完整双端目标通过。远程Git提交SHA与本地可能不同，以fetch后文件树一致为准。

## 2026-10-15 独立首次安装包；2026-10-16 恢复与同步

新增可选Windows x64独立ZIP，附带本机已验证的CPython3.13.14/Tk8.6。运行时排除site-packages、用户customize、缓存与测试目录，保留许可证和逐文件哈希。._pth隔离模块路径，正式启动入口均传-B。首次安装完整暂存后原子改名，不覆盖现有安装；已有代码更新ZIP契约不变。

上轮实际验证：本地及Windows各41项测试、Node纯协议3项、Tk/managed smoke、curl空文件及2,097,155字节通过。独立包实际GUI重启升级0.1.0→0.1.1后继续接收，故意启动失败0.1.2后恢复0.1.1；配置字节和runtime清单/哈希不变。最终独立集成测试exit0，75.57s。独立审查发现UI重启漏-B，已红→绿修复；测试提前终止进程的竞态及导入拼接错误均已修正后重跑通过。

已交付到电脑（未正式安装）：C:\Users\Lenovo\Downloads\Share-builds\Share-Windows-Standalone-0.1.0-x64-7789a9ed.zip，13,846,052字节；SHA256=7789a9ed0f51555eddb7ddf3c49eff62fe6cf7b012ec6e60bee99942890f0561。旁附.sha256。

本次恢复：临时开发目录已被清理；从GitHub分支5f41f61和Windows构建目录恢复10个源码/测试/README文件，未更改其逻辑。实时核对交付ZIP哈希仍一致；恢复后本地41/41通过，本次Windows重新回归41/41通过，22.196s，exit0；Node纯协议3/3、compileall与diff检查通过。后续以Git仓库和该记录续跑，避免依赖临时目录。

整体仍PARTIAL。独立包为ZIP+安装脚本，不是单文件EXE；未在干净虚拟机或其他Windows机器验收，runtime/稳定启动器不由代码包自更新。未发布Release、合并PR、写真实开始菜单、改变防火墙或常驻部署。

2026-10-16再次定向检查：命令行未发现hdc/hvigor/hvigorw，卸载注册表未定位DevEco，DEVECO_SDK_HOME/HOS_SDK_HOME为空；这不排除其他未登记位置。鸿蒙SDK编译、签名、HAP、真机和系统球直接drop仍NOT RUN/BLOCKED。下一步是原生工具链、签名与设备授权，不能由电脑端通过推导完整双端通过。
