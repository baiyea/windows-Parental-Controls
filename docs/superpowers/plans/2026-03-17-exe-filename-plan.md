# 打包文件名规范实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将打包后的 exe 文件名称从 `ParentControl.exe` 改为 `ParentControl.windows.{版本号}.exe`，并同步更新推送脚本和程序自身的更新机制。

**Architecture:** 修改 build.sh 和 utils/updater.py 两个文件，使打包文件名、自动更新检测和下载逻辑保持一致。

**Tech Stack:** Shell (bash), Python (re 模块)

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `build.sh` | 打包脚本，生成带版本号的 exe 文件名 |
| `utils/updater.py` | 自动更新模块，检测和下载新版本 |

---

## Chunk 1: build.sh 修改

### Task 1: build.sh 版本号去零和打包名称修改

**Files:**
- Modify: `build.sh:119-145`

- [ ] **Step 1: 在递增版本号后添加去零逻辑**

找到 build.sh 第 133 行 `NEW_VERSION="${MAJOR_VERSION}.${NEW_MINOR}"` 后添加：

```bash
# 版本号去零：1.7.09 -> 1.7.9，只去掉前导零
VERSION_NO_ZERO=$(echo "$NEW_VERSION" | sed -E 's/\.0+([0-9])/.\1/g')
```

- [ ] **Step 2: 修改打包名称**

找到 build.sh 第 107 行 `--name ParentControl`，修改为：

```bash
--name ParentControl.windows.${VERSION_NO_ZERO}
```

- [ ] **Step 3: 修改版本号文件写入**

找到 build.sh 第 139 行 `echo "$NEW_VERSION" > dist/version.txt`，修改为：

```bash
echo "$VERSION_NO_ZERO" > dist/version.txt
```

- [ ] **Step 4: 修改上传文件路径**

找到 build.sh 第 67-71 行的上传命令，修改文件路径：

```bash
upload_response=$(curl -s -X POST "${api_url}/releases/${release_id}/attach_files" \
    -H "Authorization: token ${token}" \
    -F "file=@dist/ParentControl.windows.${VERSION_NO_ZERO}.exe")
```

- [ ] **Step 5: 更新打包成功提示**

找到 build.sh 第 145 行 `dist/ParentControl.exe`，修改为：

```bash
echo -e "${GREEN}✓ 打包成功: dist/ParentControl.windows.${VERSION_NO_ZERO}.exe${NC}"
```

找到 build.sh 第 155 行 `./dist/ParentControl.exe --install`，修改为：

```bash
./dist/ParentControl.windows.${VERSION_NO_ZERO}.exe --install
```

- [ ] **Step 6: 提交代码**

```bash
git add build.sh
git commit -m "feat: 打包文件名添加版本号 (如 ParentControl.windows.1.7.9.exe)"
```

---

## Chunk 2: utils/updater.py 修改

### Task 2: utils/updater.py 自动更新逻辑修改

**Files:**
- Modify: `utils/updater.py:39-86` (check_for_update)
- Modify: `utils/updater.py:89-141` (download_update)
- Modify: `utils/updater.py:143-182` (apply_pending_update)

- [ ] **Step 1: 添加 re 模块导入**

在 utils/updater.py 第 8 行（import 语句区域）添加：

```python
import re
```

- [ ] **Step 2: 修改 check_for_update() 检测逻辑**

找到第 72-76 行：
```python
for asset in assets:
    if asset.get('name', '').endswith('.exe'):
        download_url = asset.get('browser_download_url')
```

修改为：
```python
for asset in assets:
    name = asset.get('name', '')
    if name.startswith('ParentControl.windows.') and name.endswith('.exe'):
        download_url = asset.get('browser_download_url')
```

- [ ] **Step 3: 修改 download_update() 文件名**

找到第 94 行：
```python
dest_path = os.path.join(update_dir, 'ParentControl.exe')
```

修改为：
```python
# 对版本号去零（与打包文件名一致）
latest_version_no_zero = re.sub(r'\.0+([0-9])', r'.\1', latest_version.lstrip('v'))
dest_path = os.path.join(update_dir, f'ParentControl.windows.{latest_version_no_zero}.exe')
```

- [ ] **Step 4: 修改 apply_pending_update() 文件名**

找到第 148 行：
```python
new_exe = os.path.join(update_dir, 'ParentControl.exe')
```

修改为：
```python
# 对版本号去零（与打包文件名一致）
current_version_no_zero = re.sub(r'\.0+([0-9])', r'.\1', current_version)
new_exe = os.path.join(update_dir, f'ParentControl.windows.{current_version_no_zero}.exe')
```

- [ ] **Step 5: 提交代码**

```bash
git add utils/updater.py
git commit -m "feat: 自动更新匹配新的 exe 文件名格式"
```

---

## 验收标准

1. `build.sh` 打包生成 `ParentControl.windows.1.7.9.exe`
2. 上传到 Gitee 的文件名正确
3. `dist/version.txt` 内容为去零版本号 `1.7.9`
4. 程序启动时自动更新检测能正确匹配新文件名格式
5. 自动更新下载的文件名与打包文件名一致
