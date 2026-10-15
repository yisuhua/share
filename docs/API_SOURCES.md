# 原生实现的 API 来源与边界

2026-10-15 实际读取以下 OpenHarmony 官方仓库文档；未执行文档所描述的鸿蒙运行时。引用 master 中的接口时只使用标记为 API20 或更早的能力。商业 HarmonyOS 设备上的权限策略仍需另验。

| 官方文档 | 读取到的 blob SHA | 使用范围 |
|---|---|---|
| [floatingBall](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkui/js-apis-floatingBall.md) | d867933c5a59ec41d07d27c632861dceb2b784f1 | API20设备判断/create/start/stop/click/restoreMainWindow |
| [HTTP](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-network-kit/js-apis-http.md) | 9eac7ab0822f9071fed7362fa0b3192ac95015bc | request、multipart filePath、进度、destroy；未使用API26 body |
| [File IO](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-core-file-kit/js-apis-file-fs.md) | 25fa558684a77dbf405019c66e45d1f075c9b865 | URI打开、fd stat/copy/read、close、缓存清理 |
| [File URI](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-core-file-kit/js-apis-file-fileuri.md) | 6279dbaa28d02e958ab96ef4fc3325bf6a941370 | FileUri.name读取原始名称 |
| [Crypto](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-crypto-architecture-kit/js-apis-cryptoFramework.md) | ef59b207c1110bb93669ad6b953903c282525ad1 | SHA256 Md.update/digest |
| [文件选择器](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-core-file-kit/js-apis-file-picker.md) | 917df42db312a0382040c9469d044e72e58c4581 | UIAbilityContext构造DocumentViewPicker并选择文件 |
| [图片选择器](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-media-library-kit/arkts-apis-photoAccessHelper-PhotoViewPicker.md) | d1891336793186a44eb13442b541f00d2dc50e07 | PhotoViewPicker选择图片，复用行为仍需真机验证 |
| [UDMF](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkdata/js-apis-data-unifiedDataChannel.md) | 84fce0dbac52de3ff9aeee24ed3b959265920d66 | 上传页读取UnifiedData记录；不代表系统球可接收文件 |
| [文件URI数据结构](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkdata/js-apis-data-uniformDataStruct.md) | 9d414a657562a0591e80cde1a42c627c55929218 | API15 FileUri.oriUri |
| [拖拽事件](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkui/arkui-ts/ts-universal-events-drag-drop.md) | 3e923ef43805e0194ea6a0432295665ac2b82723 | 页面onDrop/getData/setResult |
| [Preferences](https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkdata/js-apis-data-preferences.md) | 790fcd59e7ac58c2bd6256abe9acb0c7be28a11d | 应用沙箱内连接配置持久化 |

华为官方 [闪控球指导](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/floatingball-guide)、[受限权限](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/restricted-permissions) 页面已请求，但正文获取受动态页面限制；没有据此编造当前应用的权限获批或可申请结论。

没有采用此前检索到但缺少完整官方类型定义的RCP接口；选择已读取接口定义的NetworkKit文件表单路径。当前没有引入额外第三方运行时包或下载外部Skill。
