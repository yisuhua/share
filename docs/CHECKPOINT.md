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
