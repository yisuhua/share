# Share 开发约束与设计

用户已确认：使用 yisuhua/share；平板必须有跨应用悬浮入口；拖拽图片/文件或直接选取上传；电脑悬浮球接收；可设置持久默认保存目录。不得以网页内悬浮按钮替代系统悬浮入口。

当前从空仓库开始，没有已验证的旧版本。Windows receiver 是独立可验证阶段；整体状态 PARTIAL，不是可直接安装的完整双端应用。

## 本阶段实现

Python 标准库 Tk 桌面球 + 有界线程 HTTP 接收器。程序启动即监听，点击球查看记录与配置；无需逐个确认接收。默认目录为用户 Downloads/Share，可从面板修改；配置保存在 LOCALAPPDATA/Share/settings.json（Windows）。

接收器不读取、修改或公开电脑上已有文件。每个上传先写临时文件，校验长度和 SHA-256，刷盘后原子发布；同名自动加序号，不覆盖。变更目录只作用于后续开始的上传，已进行中的上传继续使用开始时的目录。正常失败清理临时文件；进程崩溃/强制退出遗留的 .share-*.part 不视为成功文件。

传输仅允许 RFC1918 IPv4/回环来源，随机配对密码验证；拒绝浏览器 Origin。HTTP 不加密，只用于可信局域网，不进行路由器端口映射。文件不自动打开或执行。最大 8 条连接；单文件默认 1 GiB；30 秒 socket 空闲超时。无自动重试以免成功回执丢失时产生不透明重复文件。

## 平板端：尚未完成的能力门禁

当前读取的 OpenHarmony 官方文档 `js-apis-floatingBall.md` blob SHA：
`d867933c5a59ec41d07d27c632861dceb2b784f1`。
https://github.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkui/js-apis-floatingBall.md

文档说明 API 20 开始支持、具有设备能力判断、create/start/update/stop、click/stateChange、恢复主窗口等接口。启动需要 `ohos.permission.USE_FLOAT_BALL`。文档中也有 API 24/26 新增接口，不能把 master 分支全部接口当作 HarmonyOS 6 可用接口。

**尚无证据证明闪控球本身可作为外部文件 drop target**。移动球的位置不等于向球拖入文件。不可伪造 onDrop 或把 ArkUI 普通组件 onDrop 当成系统球的回调。

需在用户平板和对应 DevEco SDK/签名环境完成：

1. 核对准确系统构建/API、设备能力与应用权限。
2. 编译并签名最小原生能力探针；启动球后切到其他应用，观察是否继续可见。
3. 证实点击球能唤起文件选择/上传流程。
4. 单独验证文件/图片拖向系统球是否产生可读 URI/UDMF 数据；若 API 不开放该入口，报告 BLOCKED，保留用户要求。
5. 验证文件 URI 读取、授权生命周期、后台上传、网络失败、完整性回执。

替代入口（系统小窗、分享菜单、网页、升级系统）均不自动视为批准，且不能据此宣布原目标完成。

## 测试计划

接收层：真实 loopback HTTP + 临时磁盘目录，验证认证、中文文件名、超限、哈希错误、并发同名、不完整请求、目录持久化、跨源拒绝。
桌面层：Windows 上 Tk 初始化、面板创建、目录切换、接收事件显示与退出。视觉和真实平板联调单独记录。
