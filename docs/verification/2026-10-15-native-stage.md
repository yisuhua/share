# 本轮验证记录（记录摘要，非原始终端转储）

## 当前执行环境

Python 3.12.14：`python3 -m unittest discover -s tests -v`，16 tests，OK。

`python3 tests/curl_interop.py`：真实 curl multipart，0 bytes 与2,097,155 bytes 两个文件均取得匹配回执，磁盘字节等于输入。

Node v24.19.0：`node --test tests/client_contract.test.mjs`，3 tests / 3 pass / 0 fail。内容为私有IPv4目标校验、旧接收器兼容判断、201回执的长度/哈希匹配与畸形输入拒绝。

Python compileall与git diff --check通过。11个JSON配置及SVG XML可解析；7个非ArkUI源码文件通过Node语法检查。没有把这些检查称为DevEco schema检查或ArkTS编译。

## Windows 实机

Python 3.13.14（AMD64）。实际运行当前接收器与测试文件的独立副本，服务仅绑定127.0.0.1临时端口。

1. `py -3 -m unittest discover -s tests -v`：16 tests，8.455s，OK。
2. `py -3 tests/curl_interop.py`：0 bytes与2,097,155 bytes，均CURL_MULTIPART_PASS。
3. `py -3 tests/windows_smoke.py`：WINDOWS_TK_SMOKE_PASS。
4. 整个验证脚本退出码0，12.47s；测试服务停止，未部署常驻应用。

工作目录：`C:\Users\Lenovo\AppData\Local\Temp\Share-native-wire-20261015-1x4vrvig`。

## 独立源代码审查

使用requesting-code-review Skill的独立只读审查。发现一个重要问题（异步配置读取可能改变操作中的目标电脑）和一个较小问题（发送失败后缓存清理警告被覆盖），均已修改，并由审查者针对改动回看。临时缓存目录同时改为原生mkdtemp创建。

审查未认定原生构建、签名、设备权限、文件URI授权、直接系统球文件拖入或真实后台行为可用；PR保持draft。这些源代码修改未改变Python接收器，未重复已通过的Windows接收测试。

## 不覆盖的范围

未运行DevEco构建、鸿蒙签名、HAP安装、真机系统球、平板跨应用拖拽、实际Wi-Fi传输、1GiB文件、后台持续上传或长时稳定性测试。上述状态保持NOT RUN / BLOCKED，不存在完整双端Latest Valid。
