# HarmonyOS 原生客户端工作区

**状态：源码已实现，原生编译 / 签名 / 真机运行 NOT RUN。不是可安装 HAP，也不是已验证的平板版本。**

目标为 HarmonyOS 6.0.0 / API 20。只调用已核对的 API 20 或更早接口，不把 API 24/26 的新窗口功能混入目标。

## 当前源码路径

- `SystemBall.ets`：能力检查、启动系统闪控球、点击恢复本应用主窗口、停止；启动权限失败原样显示错误。
- `Index.ets`：电脑地址/配对密码持久化、选择图片、选择文件、顺序发送、结果记录。
- `NativeSender.ets`：按授权 URI 打开文件，复制到应用缓存，分段计算 SHA-256，使用 NetworkKit 的 filePath multipart 上传，校验电脑 201 回执的长度与哈希，再清理缓存。
- `DropFiles.ets`：**上传页**的文件 URI / 图片拖入适配。不是系统球的 drop 回调；不同来源应用与授权仍需实测。
- `Protocol.ts`：跨平台可执行的地址/协议/回执校验逻辑。它的 Node 测试不等于 ArkTS 编译或鸿蒙运行通过。

未设置 `remoteFileName`，避免原生 filePath 上传路径尝试整文件读入内存；原始文件名由查询参数传递，电脑仍检查文件名。单文件上限由电脑返回，不自行降低 1 GiB 默认上限。复制缓存需要额外磁盘空间，复制失败会终止该文件。

HTTP 仅用于受信任的同一局域网；仅接受用户明确填写的 RFC1918 IPv4 地址。没有云端中转、自动重试或断点续传。发送期间保持页面前台；后台持续上传尚未承诺或验证。失去回执属于结果不确定，先在电脑核对，避免重复上传。

## 在 DevEco 中构建和检查

本轮环境检查和可继续操作见 [工具链检查记录](../docs/verification/2026-10-15-tablet-toolchain.md)。建议在官方下载中心选择 **DevEco Studio 6.0.0 Release / Command Line 6.0.0.878**，对应 API 20；不要直接用下载页默认的新版本替换工程目标。若下载页面要求登录或确认协议，由用户在官方页面完成。

1. 从 [华为官方下载入口](https://developer.huawei.com/consumer/cn/deveco-studio/)安装支持 HarmonyOS 6 / API 20 的 DevEco Studio 与 SDK，打开本目录。
2. 先进行同步和未签名构建，记录完整编译输出。当前未运行这一关；若本机 DevEco 模型版本与工程配置不兼容，应基于真实错误修正配置，不直接声称兼容。
3. 在 Project Structure → Signing Configs 中为用户自己的调试设备配置签名。仓库不含证书、私钥、密码或设备绑定文件；不要提交这些文件。
4. 按官方 [受限权限说明](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/restricted-permissions)核对 `USE_FLOAT_BALL` 的申请条件。写入 manifest 不等于权限获批；个人/当前应用类别能否取得该权限也未验证。
5. 安装到平板后按 `../docs/TABLET_ACCEPTANCE.md` 逐项验收。若返回 201 权限错误或 801 能力不支持，保存原始日志并保持 BLOCKED；不把普通页面按钮算成跨应用球。

## 关键未解条件

系统球本体是否能直接接收拖入文件尚无可用公开回调证据。当前源代码实现“点系统球 → 返回原生上传页 → 选择/拖入上传”的路径，**不能把它描述成已经实现“文件直接拖到系统球上即发送”**。用户原要求保持不变；替代入口不自动通过该项验收。
