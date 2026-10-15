# 平板端工具链检查

Project: yisuhua/share；分支 codex/share-floating-receiver；整体 PARTIAL。
本轮只恢复构建前置条件，未改变 ArkTS 源码或工程 API 目标。

## 实际检查

- Windows LAPTOP-PP0NA67R：命令行未找到 java、hdc、hvigor、hvigorw；HKLM/HKCU 已登记应用中未定位 DevEco。SDK 环境变量为空。范围有限，不代表扫描了所有磁盘位置。
- D 盘剩余约 257 GB，可供项目隔离工具链；本轮未安装 DevEco、未修改系统 PATH、未连接平板调试会话。
- 华为官方下载中心前端可访问；按公开前端声明请求工具列表，服务返回 `90910008`（缺少日期头）。依据同一公开前端补充日期及随机请求序号后，返回 `90910011`（缺少 X-HD-CSRF）。未取得下载列表或 ZIP，未构造会话凭证、未登录、未代签协议。
- 官方页面介绍的 `@deveco/deveco-cli@1.3.0-stable` 仅下载压缩包并读取说明，未安装或执行。其说明仍要求另行准备 DevEco / Command Line Tools，未解决 API20 SDK 缺失，故不引入工程依赖。
- 未使用网上的第三方工具链重打包，也未把 OpenHarmony 工具包当作商业 HarmonyOS API20 SDK。

## 继续所需的一步

在电脑访问 [华为官方下载中心](https://developer.huawei.com/consumer/cn/download/command-line-tools-for-hmos)，选择 Windows x64 的 **6.0.0 Release / 6.0.0.878** 工具包（或配套 DevEco Studio）。完成页面实际要求的登录/协议步骤，解压到项目专用位置，例如 `D:\Share-development\toolchain`，然后提供实际解压路径。无需提供账号密码、证书或私钥。

取得工具后，先核对内置 SDK 的 API20 元数据和工具版本，再对 `harmonyos/` 执行同步和未签名 HAP 构建，保存完整日志并逐项修复实际编译错误。源码包可以在 DevEco 中直接打开 `harmonyos/`；菜单名称以所装版本为准。

构建通过之后才进行用户设备签名与安装。`USE_FLOAT_BALL` 是否获准、是否跨应用可见、点击是否恢复上传页、图片/文件传输是否一致，均按 [TABLET_ACCEPTANCE.md](../TABLET_ACCEPTANCE.md) 取得设备证据。系统球直接接收文件拖入仍 BLOCKED。

## 官方依据

- [获取 Command Line Tools](https://developer.huawei.com/consumer/en/doc/harmonyos-guides/ide-commandline-get)：工具包带配套 SDK，获取入口为下载中心。
- [DevEco Studio 6.0.0 配套关系](https://developer.huawei.com/consumer/en/doc/harmonyos-releases/deveco-studio-new-features-600)：6.0.0.878 配套 API20、hvigorw 6.20.2。配套关系不等于本机已具备工具。
- [应用升级适配](https://developer.huawei.com/consumer/en/doc/harmonyos-releases/upgrade-adaptation)：6.0.0 起配套 SDK 内置；保持当前工程目标，不隐式迁移到 API26。

原生编译、签名、HAP、真机运行：**NOT RUN**。本轮没有可安装平板包，也没有新的原生通过结果。
