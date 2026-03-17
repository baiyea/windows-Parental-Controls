# 打包文件名规范设计

## 需求背景

将打包后的 exe 文件名称从 `ParentControl.exe` 改为包含版本号的格式 `ParentControl.windows.{版本号}.exe`，并同步更新推送脚本和程序自身的更新机制。

## 当前状态

| 文件 | 当前行为 |
|------|----------|
| `build.sh:107` | `--name ParentControl` → `dist/ParentControl.exe` |
| `build.sh:67-71` | 上传 `dist/ParentControl.exe` 到 Gitee |
| `utils/updater.py:72-76` | 检测 `.exe` 结尾的文件作为更新包 |

版本号格式：`1.7.09` → 打包名称使用 `1.7.9`（去掉前导零）

## 修改方案

### 1. build.sh 修改

#### 1.1 版本号处理（新增）
在递增版本号后，增加去零逻辑：
```bash
# 版本号去零：1.7.09 -> 1.7.9，只去掉前导零
VERSION_NO_ZERO=$(echo "$NEW_VERSION" | sed -E 's/\.0+([0-9])/.\1/g')
```
这样 `1.7.09` → `1.7.9`，`1.7.10` → `1.7.10`

#### 1.2 打包名称修改
```bash
--name ParentControl.windows.${VERSION_NO_ZERO}
```
生成 `dist/ParentControl.windows.1.7.9.exe`

#### 1.3 上传文件路径修改
```bash
-F "file=@dist/ParentControl.windows.${VERSION_NO_ZERO}.exe"
```

#### 1.4 版本号文件
```bash
echo "$VERSION_NO_ZERO" > dist/version.txt
```

### 2. utils/updater.py 修改

#### 2.1 download_update() 文件名修改
```python
# 第94行
# 对版本号去零（与打包文件名一致）
import re
latest_version_no_zero = re.sub(r'\.0+([0-9])', r'.\1', latest_version.lstrip('v'))
dest_path = os.path.join(update_dir, f'ParentControl.windows.{latest_version_no_zero}.exe')
```

#### 2.2 check_for_update() 检测逻辑修改
修改第72-76行的 exe 检测逻辑，匹配新的文件名格式：
```python
for asset in assets:
    name = asset.get('name', '')
    if name.startswith('ParentControl.windows.') and name.endswith('.exe'):
        download_url = asset.get('browser_download_url')
        return True, download_url
```

#### 2.3 apply_pending_update() 文件名修改
```python
# 第148行
# 对版本号去零（与打包文件名一致）
import re
current_version_no_zero = re.sub(r'\.0+([0-9])', r'.\1', current_version)
new_exe = os.path.join(update_dir, f'ParentControl.windows.{current_version_no_zero}.exe')
```

## 文件清单

| 文件 | 修改类型 |
|------|----------|
| `build.sh` | 修改 |
| `utils/updater.py` | 修改 |

## 风险评估

- **低风险**: 文件名修改不影响程序核心功能
- **兼容性**: 旧版本无法通过自动更新升级（需手动重装一次）

## 验收标准

1. `build.sh` 打包生成 `ParentControl.windows.1.7.9.exe`
2. 上传到 Gitee 的文件名正确
3. `dist/version.txt` 内容为去零版本号 `1.7.9`
4. 程序启动时自动更新检测能正确匹配新文件名格式
5. 自动更新下载的文件名与打包文件名一致
