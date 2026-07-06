# 自动更新安装测试方案

## 目标

验证客户端能够从 Gitee Release 检测新版本、下载更新包、在下次启动时替换当前 exe、写入 `version.txt`，并启动新版本程序。

当前实现涉及：

- `main.py`：启动时调用 `run_auto_update()`，如果返回 `update_applied` 则退出当前程序。
- `utils/updater.py`：检查 Gitee 最新 Release、下载 exe、生成 `update.bat` 应用更新。
- `config.py`：通过 `version.txt` 或 `pyproject.toml` 获取当前版本。
- `build.sh`：打包 `ParentControl.windows.{版本}.exe` 并上传到 Gitee Release。

## 当前更新链路

```text
程序启动
  -> apply_pending_update()
      -> update/ 目录有 ParentControl.windows.*.exe?
          -> 打包模式: 生成 update.bat，退出当前进程，由 bat 覆盖 exe、写 version.txt、重启
          -> 开发模式: 跳过
  -> check_for_update()
      -> 请求 https://gitee.com/api/v5/repos/degao/parental-control/releases/latest
      -> 比较 tag_name 与当前版本
      -> 查找 ParentControl.windows.*.exe asset
  -> download_update()
      -> 下载到 update/ParentControl.windows.{版本}.exe.tmp
      -> 完成后重命名为 .exe
  -> 本次继续运行旧版本，下次启动应用更新
```

## 风险说明

当前 `GITEE_API_URL` 硬编码到生产仓库：

```python
https://gitee.com/api/v5/repos/degao/parental-control/releases/latest
```

因此，只要生产 Gitee 仓库发布更高版本 Release，所有开启自动更新且能访问 Gitee 的客户端都会检测到。完整安装测试应优先使用测试仓库或测试构建，避免误触发真实用户更新。

推荐分层测试：

1. 自动化单元测试：不访问网络、不运行真实 bat。
2. 本地集成测试：使用临时目录模拟打包后的 exe 目录。
3. 测试仓库端到端测试：用测试 Gitee repo 或测试构建验证真实下载和替换。
4. 生产发布前冒烟测试：只验证元数据、文件名和版本号，确认无误后发布。

## 测试环境

### 开发机自动化测试

- Windows
- Python 3.13
- `uv`
- 不需要真实 Gitee token
- 不需要真实 exe

运行命令：

```bash
uv run python -m unittest discover -s tests -v
```

### 打包安装测试

- Windows 测试机或虚拟机
- 能运行 PyInstaller 打包产物
- 能访问 Gitee
- 测试目录示例：

```text
C:\ParentControlUpdateTest\
  ParentControl.windows.1.7.12.exe
  version.txt
  config.json
  update\
```

### 测试账号和仓库

推荐准备独立测试仓库：

```text
degao/parental-control-update-test
```

或使用测试构建临时修改 `GITEE_API_URL` 指向测试仓库。不要直接用生产仓库做首次端到端验证。

## 版本和文件命名规则

测试使用两版：

| 角色 | 示例版本 | 文件名 |
|------|----------|--------|
| 旧客户端 | `1.7.12` | `ParentControl.windows.1.7.12.exe` |
| 新 Release | `1.7.13` | `ParentControl.windows.1.7.13.exe` |

Release 要求：

- `tag_name`: `v1.7.13`
- asset 名称：`ParentControl.windows.1.7.13.exe`
- asset 必须有 `browser_download_url`

## 自动化测试用例

### UT-01 版本号解析

目的：确认版本比较稳定。

覆盖：

- `1.7.9 < 1.7.10`
- `v1.7.13 == 1.7.13`
- `1.7 < 1.7.1`

期望：

- `parse_version()` 返回可比较的整数元组。
- 不出现字符串比较导致 `1.7.10 < 1.7.9` 的问题。

### UT-02 自动更新禁用

目的：确认配置关闭时不会访问 Gitee。

步骤：

1. 设置 `config.g_config["auto_update"]["enabled"] = False`。
2. mock `urllib.request.urlopen`。
3. 调用 `check_for_update()`。

期望：

- 返回 `(False, None, None)`。
- `urlopen` 未被调用。

### UT-03 检测到更高版本和正确 asset

目的：确认 release 元数据解析正确。

模拟 Gitee 响应：

```json
{
  "tag_name": "v1.7.13",
  "assets": [
    {
      "name": "ParentControl.windows.1.7.13.exe",
      "browser_download_url": "https://example.test/ParentControl.windows.1.7.13.exe"
    }
  ]
}
```

期望：

- `check_for_update()` 返回：

```python
(True, "https://example.test/ParentControl.windows.1.7.13.exe", "1.7.13")
```

### UT-04 最新版本不高于当前版本

目的：确认不会重复下载同版本或低版本。

场景：

- 当前版本 `1.7.13`，latest `v1.7.13`
- 当前版本 `1.7.13`，latest `v1.7.12`

期望：

- 返回 `(False, None, None)`。

### UT-05 release 缺少匹配 exe

目的：确认只接受正确命名的 Windows exe。

场景：

- asset 是 `ParentControl.exe`
- asset 是 `ParentControl.windows.1.7.13.zip`
- asset 是 `Other.windows.1.7.13.exe`

期望：

- 返回 `(False, None, None)`。
- 不下载错误资产。

### UT-06 检查更新网络失败

目的：确认网络失败不影响程序启动。

步骤：

1. mock `urllib.request.urlopen` 抛出 `urllib.error.URLError`。
2. 调用 `check_for_update()`。

期望：

- 返回 `(False, None, None)`。
- 记录错误日志。
- 不抛出异常到主流程。

### UT-07 下载成功

目的：确认下载使用 `.tmp` 中转并最终重命名。

步骤：

1. 使用 `tempfile.TemporaryDirectory()` 作为 update 目录。
2. mock `get_update_dir()` 返回临时目录。
3. mock `urlopen()` 返回分块内容。
4. 调用 `download_update(url, "1.7.13")`。

期望：

- 返回路径以 `ParentControl.windows.1.7.13.exe` 结尾。
- 目标 exe 文件存在，内容等于模拟下载内容。
- `.tmp` 文件不存在。

### UT-08 下载中断清理 tmp

目的：确认半成品不会被下一次启动误识别。

步骤：

1. mock response 在读取中途抛出异常。
2. 调用 `download_update()`。

期望：

- 返回 `None`。
- `.tmp` 文件被删除。
- 不存在完整 `.exe`。

### UT-09 磁盘空间不足

目的：确认可用空间低于 50MB 时跳过下载。

步骤：

1. mock `shutil.disk_usage()` 返回 free 小于 `50 * 1024 * 1024`。
2. 调用 `download_update()`。

期望：

- 返回 `None`。
- 不调用 `urlopen()`。

### UT-10 开发模式不应用更新

目的：确认开发运行不会误生成更新脚本。

步骤：

1. 临时 update 目录里放 `ParentControl.windows.1.7.13.exe`。
2. 确保 `sys.frozen` 为 false。
3. 调用 `apply_pending_update()`。

期望：

- 返回 `False`。
- 不生成 `update.bat`。
- 不调用 `subprocess.Popen()`。

### UT-11 打包模式生成 update.bat

目的：确认待更新包会转换为安装脚本。

步骤：

1. 使用临时目录模拟 exe 所在目录。
2. 设置：

```python
sys.frozen = True
sys.executable = r"C:\temp\ParentControl.windows.1.7.12.exe"
```

3. 在 `update/` 下放 `ParentControl.windows.1.7.13.exe`。
4. mock `subprocess.Popen()`。
5. 调用 `apply_pending_update()`。

期望：

- 返回 `True`。
- 生成 `update.bat`。
- bat 内容包含：
  - `copy /y "{new_exe}" "{current_exe}"`
  - `del "{new_exe}"`
  - `echo 1.7.13 > "{version_txt}"`
  - `start "" "{current_exe}"`
- `subprocess.Popen()` 被调用，`cwd` 是 exe 所在目录。

### UT-12 run_auto_update 优先应用待更新

目的：确认有待更新文件时不再检查网络。

步骤：

1. mock `apply_pending_update()` 返回 `True`。
2. mock `check_for_update()`。
3. 调用 `run_auto_update()`。

期望：

- 返回 `"update_applied"`。
- `check_for_update()` 未被调用。

### UT-13 run_auto_update 下载完成

目的：确认发现新版本后会下载。

步骤：

1. mock `apply_pending_update()` 返回 `False`。
2. mock `check_for_update()` 返回 `(True, "https://example.test/new.exe", "1.7.13")`。
3. mock `download_update()` 返回下载路径。
4. 调用 `run_auto_update()`。

期望：

- 返回 `"download_complete"`。
- `download_update()` 收到 URL 和版本号。

### UT-14 main 在 update_applied 后退出

目的：确认更新脚本启动后当前进程退出，不继续启动控制器。

步骤：

1. mock `main.run_auto_update()` 返回 `"update_applied"`。
2. mock `main.sys.exit` 抛出 `SystemExit`。
3. mock `SingleInstance` 和 `ParentControl`。
4. 调用 `main.main()`。

期望：

- 触发 `SystemExit`。
- 不创建 `SingleInstance`。
- 不启动 `ParentControl`。

## 本地集成测试

### IT-01 模拟已下载更新包的安装脚本生成

目的：不连接 Gitee，验证“待更新包 -> update.bat”的本地链路。

步骤：

1. 创建临时目录：

```text
temp_app\
  ParentControl.windows.1.7.12.exe
  update\
    ParentControl.windows.1.7.13.exe
```

2. 在 Python 测试中设置：

```python
sys.frozen = True
sys.executable = temp_app / "ParentControl.windows.1.7.12.exe"
```

3. mock `subprocess.Popen()`，调用 `apply_pending_update()`。

期望：

- 生成 `temp_app/update.bat`。
- `run_auto_update()` 返回 `"update_applied"`。
- 主程序后续会退出。

### IT-02 模拟下载完整链路

目的：验证 `check_for_update()` 和 `download_update()` 串联。

步骤：

1. mock Gitee latest release JSON。
2. mock exe 下载响应。
3. mock 当前版本为 `1.7.12`。
4. 调用 `run_auto_update()`。

期望：

- 返回 `"download_complete"`。
- `update/ParentControl.windows.1.7.13.exe` 存在。
- 不生成 `update.bat`，因为应用更新发生在下一次启动。

## 打包安装端到端测试

### E2E-01 测试仓库真实更新

目的：验证真实 exe、真实网络、真实脚本替换。

前提：

- 使用测试仓库或测试构建，避免影响生产客户端。
- 旧版 exe：`ParentControl.windows.1.7.12.exe`
- 新版 release：`v1.7.13`
- 新版 asset：`ParentControl.windows.1.7.13.exe`

步骤：

1. 在测试机创建干净目录：

```text
C:\ParentControlUpdateTest\
```

2. 放入旧版 exe 和旧版 `version.txt`：

```text
ParentControl.windows.1.7.12.exe
version.txt    # 内容为 1.7.12
```

3. 启动旧版程序。
4. 查看日志，确认出现：

```text
当前版本: 1.7.12, 最新版本: 1.7.13
发现新版本
更新包下载成功
更新包已下载，请重启应用以完成更新
```

5. 退出程序。
6. 再次启动旧版 exe。
7. 确认程序立即退出，`update.bat` 开始执行。
8. 等待 5 秒。
9. 检查：

```text
ParentControl.windows.1.7.12.exe 被新文件覆盖
version.txt 内容为 1.7.13
update\ParentControl.windows.1.7.13.exe 已删除
update.bat 已删除
程序重新启动
```

10. 查看托盘版本号或日志，确认当前版本为 `1.7.13`。

通过标准：

- 不需要手动复制 exe。
- 更新后程序能自动重新启动。
- `version.txt` 与新版本一致。
- `update/` 下不残留完整更新包。

### E2E-02 断网启动

目的：验证更新失败不影响主程序启动。

步骤：

1. 断开网络或屏蔽 Gitee。
2. 启动程序。

期望：

- 日志记录检查更新失败。
- 程序继续进入主控制流程。
- 不弹出错误阻塞用户。

### E2E-03 无权限目录

目的：验证安装目录不可写时不会破坏当前版本。

步骤：

1. 将测试程序放到需要管理员权限写入的目录。
2. 使用普通用户启动。
3. 触发更新下载或应用。

期望：

- 下载或写 bat 失败时记录日志。
- 当前 exe 不被破坏。
- 下次启动仍能运行旧版。

### E2E-04 文件名不匹配的 release

目的：验证错误 asset 不会被下载。

步骤：

1. 发布测试 release，tag 高于当前版本。
2. asset 使用错误命名，例如 `ParentControl.exe` 或 `.zip`。
3. 启动客户端。

期望：

- 检测到 tag 高版本，但没有匹配 exe。
- 不下载文件。
- 不创建 `update/ParentControl.windows.*.exe`。

## 生产发布前检查清单

发布前必须确认：

- [ ] `pyproject.toml` 版本号已递增。
- [ ] `dist/version.txt` 内容与 exe 文件名版本一致。
- [ ] exe 文件名为 `ParentControl.windows.{版本}.exe`。
- [ ] Gitee release tag 为 `v{版本}`。
- [ ] Gitee release asset 名称与 exe 文件名完全一致。
- [ ] Release asset 有可访问的 `browser_download_url`。
- [ ] 使用测试机从旧版本完成一次升级。
- [ ] 日志中没有更新应用失败。

## 建议新增的测试文件

新增：

```text
tests/test_updater.py
```

建议将 UT-01 到 UT-13 放入该文件。

扩展：

```text
tests/test_update_script_security.py
```

建议加入 UT-14，覆盖 `main.py` 对 `update_applied` 的退出行为。

## 建议执行顺序

1. 先补自动化单元测试，确保更新模块逻辑稳定。
2. 再做本地集成测试，验证临时目录和 bat 生成。
3. 再用测试仓库做端到端更新。
4. 最后再发布生产 release。

## 已知限制

当前实现没有以下能力，测试方案只能记录风险，不能证明其安全性：

- 没有下载文件 hash 校验。
- 没有数字签名校验。
- 没有 release 来源白名单之外的完整校验。
- 没有回滚机制。
- `GITEE_API_URL` 硬编码，端到端测试生产仓库会影响真实客户端。

后续如要强化更新安全，应先增加 hash 或签名校验，再补对应测试。
