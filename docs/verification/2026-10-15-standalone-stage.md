# Windows 独立安装包验证与恢复记录

范围：电脑端首次安装包和既有代码更新兼容。项目整体PARTIAL，平板端未完成原生验收。

## 来源和资产

运行时来源为Windows已验证的标准CPython3.13.14 AMD64/Tk8.6安装；未替换系统Python或安装第三方依赖。工具：`py -3 -B tools/package_windows.py --bundle-runtime`。

构建/源码目录：`C:\Users\Lenovo\AppData\Local\Temp\Share-standalone-20261015-fma7zkwn`。

交付：`C:\Users\Lenovo\Downloads\Share-builds\Share-Windows-Standalone-0.1.0-x64-7789a9ed.zip`。

大小13,846,052字节；SHA256 `7789a9ed0f51555eddb7ddf3c49eff62fe6cf7b012ec6e60bee99942890f0561`；复制后核对一致。ZIP中14个应用/安装/README文件与Windows构建源逐字节比较，mismatches=[]，runtime另外校验全文件清单与哈希。

## 2026-10-15 已执行证据

- 本地与Windows41项Python测试通过，Windows最终23.457s，exit0；Node纯协议3/3；compileall与git diff --check通过。
- 新增7项运行时测试覆盖排除规则和路径、缺文件、篡改/额外文件、越界清单、首次安装复制、损坏不安装和实际UI启动参数。
- Windows managed smoke通过，含中文路径CMD模板启动；独立包使用附带解释器创建Tk、导入SSL/哈希，并通过Tk smoke及真实curl multipart 0、2,097,155字节上传。
- 独立测试将PATH限制为Windows System32，设置无效PYTHONHOME及带sitecustomize探针的PYTHONPATH。sys.prefix/sys.path只含安装后的runtime/Lib/DLLs，探针未执行。
- 实际Desktop/UpdateWindow.restart启动更新helper；0.1.0保存before.txt，0.1.1保存after.txt。测试新版仅添加记录PID的薄包装，实际接收/配置/更新逻辑来自项目。
- 等启动器释放startup.lock后，0.1.2 fixture故意抛启动错误；helper返回非0并恢复0.1.1，recovered.txt继续保存；配置字节和runtime文件清单/哈希不变。
- 最终 `tests/windows_standalone_smoke.py --reuse-build` exit0，75.57s，使用上述同一SHA资产。标记REAL_GUI_UPGRADE_READY_AND_LAUNCHER_FINISHED、REAL_GUI_RESTART_RUNTIME_UNCHANGED_PASS、WINDOWS_STANDALONE_SMOKE_PASS。
- 测试服务/子进程正常清理，仅回环监听；未写用户正式安装、开始菜单或防火墙。

## 问题闭环

1. 审查发现实际UI重启漏-B，直接调用helper的测试没有覆盖它。补实际restart参数测试，先FAIL再修复PASS；真实GUI更新后验证runtime不变。
2. 测试在TCP可连后立即终止新版，此时启动器尚未观察ready并释放启动锁，第二helper被正常门禁拒绝，清理撞上收尾进程。测试改为OS锁条件等待，紧急清理限制在本测试runtime完整路径前缀；产品门禁和断言未放宽。
3. 补测试时一次字符串替换误改ReceiverServer导入；已纠正并抽取驱动import实际执行检查，再从同一资产完成验证。

独立代码审查及定向回看未发现剩余Critical/Important，但不替代上列执行证据。

## 2026-10-16 恢复

开发临时目录被清理，未同步部分从Windows构建源恢复，不重写实现。当前重新核对交付ZIP存在且SHA一致；本地恢复后41测试通过，17.115s。本次Windows重新回归41/41通过，22.196s，进程exit0；本地Node纯协议3/3、compileall与diff检查通过。仅恢复源码与验证记录，不把历史记录写成新执行。

定向工具链检查未发现hdc/hvigor/hvigorw命令、已登记DevEco或相关SDK环境变量。原生编译/签名/真机仍NOT RUN。

## 限制

未测试无Python干净虚拟机、其他Windows或ARM64。证据是用户真实Windows下附带解释器与路径隔离运行；不把ChatGPT环境当Windows。未执行线上GitHub资产升级、发布Release或合并PR。runtime及稳定启动器不自更新；ZIP+脚本不是单文件EXE；哈希/许可证不等于发布者代码签名。平板仍没有可安装HAP及系统球本体文件drop证据。
