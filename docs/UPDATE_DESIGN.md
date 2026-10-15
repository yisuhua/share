# 应用内更新：已确认目标与实施计划

用户选择应用内更新。目标：安装一次后在Share中检查、下载并更新，保留默认接收目录、配对密码和接收文件。普通电脑更新不卸载旧应用；鸿蒙通过官方更新服务，不冒充系统安装权限。

## 电脑端

保持现有Python3.11+运行环境。首次安装脚本建立用户级管理目录，稳定启动器和版本指针独立于版本文件；后续更新包仅含share_receiver Python程序和校验清单。

通过GitHub官方latest release接口检查稳定版，固定yisuhua/share仓库与安装包名称；要求资产SHA-256、尺寸和版本正确。下载HTTPS、校验整体哈希，检查ZIP路径/符号链接/重复文件/展开尺寸、每文件哈希和Python语法后放入新版本目录。失败不改变当前指针。

配置仍位于LOCALAPPDATA/Share/settings.json；程序版本位于LOCALAPPDATA/Share/program/releases/<version>。更新过程不删除旧版本、不迁移或清空用户数据。下载准备完成后，仅在接收连接为空时暂停新连接，由独立启动器等待旧进程结束，再切换指针并启动新版；启动进程和桌面/服务就绪握手失败时尝试恢复旧版本。启动器串行化启动，运行中的程序持有单实例锁。保留显式回退入口。源码运行显示需要首次安装，不能自改git工作区。

## 鸿蒙端

AppGalleryKit官方checkAppUpdate后，在明确返回新版本时调用showUpdateDialog。先检查系统能力；未上架开发包明确提示渠道未开通，不声称已是最新版。包名、签名和版本号保持更新兼容。上架和权限申请未获本轮发布授权，故不进行外部发布。真实SDK/签名/设备验证仍NOT RUN。

## 执行任务

- [x] tests/test_updates.py：先验证版本、下载校验、恶意ZIP、原子切换、保留数据、回退和失败路径。
- [x] share_receiver/updates.py、version.py：版本检查、下载和安全stage/activate/rollback接口。
- [x] tools/package_windows.py、install_windows.py、launcher.pyw、install_windows.cmd：初次安装与版本包生成、稳定启动；不提供伪造EXE。
- [x] core.py与update_ui.py：更新期间空闲门禁和应用内更新界面；不阻断正在上传的文件。
- [x] 鸿蒙StoreUpdates.ets和Index.ets：官方更新入口与未开通状态。
- [x] 当前环境及Windows临时目录实测；独立代码审查；更新同一GitHub PR和Checkpoint。

## 验证焦点

1. 新版清单缺少digest、跨仓库URL、降级、预发布，不应被静默当成可安装更新。
2. 下载不完整、校验失败、磁盘错误、ZIP越界不改变当前版本和数据。
3. 更新与上传同时发生时，重启必须等待接收连接空闲。
4. 更新只切换程序目录；配置密码和接收文件字节保持不变。
5. 鸿蒙网络/服务失败或未上架不等于最新版；未运行的原生路径不进入PASS。

启动就绪上限60秒，等待期间不阻塞UI；若超时终止未就绪的子进程后尝试回退。启动完成后不监控后续运行崩溃。稳定启动器与Python运行时不由当前代码更新包更新。线上GitHub Release和原生设备路径仍待实测，不能以本地fixture通过替代。

## 可选独立首次安装包

沿用代码更新ZIP契约，新增Standalone-x64首次安装ZIP，附带已验证CPython3.13.14/Tk8.6，不改系统Python。runtime置于program/runtime，应用仍位于program/releases/<version>；精简Setup保留。

首次安装先在同父目录完整暂存，校验runtime后原子改名；已有目录不覆盖。._pth隔离模块路径，所有正式入口使用-B，稳定启动器明确插入应用版本目录。runtime与稳定启动器仍不通过代码包更新。本包不是单文件EXE，电脑端通过不代表平板完成。
