# 应用内更新验证记录

日期：2026-10-15。范围：Windows电脑更新实现；鸿蒙仅源码接入。

## PASS

- 本地 `python -m unittest discover -s tests -p 'test_*.py' -q`：34 tests，exit0。
- Windows Python3.13.14同命令：34 tests，21.168s，exit0。包含19个真实HTTP/磁盘测试、15个更新/启动器/门禁测试。
- Node纯协议测试3/3；Python compileall；git diff --check。
- Windows `tests/windows_smoke.py`：Tk置顶球、面板、更新窗口、错误状态、隐藏再打开，exit0。
- Windows `tests/windows_managed_smoke.py`：在含中文目录的临时路径首次安装，实际加载安装后模块；模拟发布元数据和本地已构造包下载（不连接GitHub），真实暂存新版并保持旧指针；真实未完成连接阻止重启；空闲后检查独立启动器参数含绝对配置；配置字节不变，exit0。
- managed smoke使用与开始菜单相同CMD模板，实际通过pythonw启动中文路径的探针脚本。未写真实开始菜单。
- Windows curl multipart空文件、2,097,155字节，实际文件字节和回执SHA核对，exit0。
- 临时进程/服务均退出；仅回环监听。工作目录：`C:\Users\Lenovo\AppData\Local\Temp\Share-update-verified-20261015-1l6ih2i3`。

更新测试覆盖：固定来源/版本、缺少digest、损坏下载、越界ZIP/大小/重复Windows别名/符号链接、文件hash、外部语法错误ZIP、原子切换和回退、旧程序与配置文件保留、延迟5.5秒后失败回退、普通损坏启动及显式回退、相对配置路径、运行中重复启动不切换、并发接收门禁。使用临时目录、测试包及子进程，不发布实际Release。

## 发现并修复

早期Windows全量测试有WinError10053；隔离复现请求头后20ms发送3字节非法文件名请求，原回复20/20错误，补读后0/20。最终实现只对early POST拒绝、唯一长度<=8192且非chunked的请求补读；read1和绝对250ms截止，超大请求不等，逐字节发送也不延长整体预算。19接收回归含延迟体、缺失/大体、慢发体，最终Windows34全量通过。客户端主动中断测试仍可出现正常的“Client disconnected before receipt”日志，不代表保存成功。

独立代码审查多轮定向回看，已修复Important；最后定向deadline及507检查复核未发现新的Important。审查结论不替代执行测试。

## NOT RUN / 限制

- GitHub最新Release在线查询、真实资产下载、正式0.1.0到0.1.1端到端升级：尚无发布资产，不能用fixture替代。HTTPS下载按GitHub资产digest校验，未加入独立发布者代码签名。
- 未验证升级Python/Tk运行时或第三方依赖；当前包仅更新平铺share_receiver Python代码，稳定启动器不自更新。
- 启动器等待服务/界面就绪最多60秒；只处理启动阶段失败，不监控成功就绪后的运行期崩溃。
- 首次安装不是独立EXE，需要Python3.11+和Tk。程序仍为部分交付，暂无可安装平板HAP。
- 鸿蒙AppGalleryKit：SDK编译、枚举/syscap、正式签名/发布、真机更新NOT RUN。开发开关false，未上架不显示“最新”。
- 系统球本体文件drop、真实平板跨应用/双端网络仍BLOCKED/NOT RUN。
