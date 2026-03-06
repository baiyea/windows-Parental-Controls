# 托盘版本号功能设计

## 目标

- 托盘菜单移除分隔线 "-"
- 托盘菜单新增"版本号"显示项
- 版本号格式: 1.7.xx，每次执行 build.sh 递增

## 版本号管理

### 存储位置
- `pyproject.toml` 中定义: `version = "1.7.00"`

### 读取
- `config.py` 中添加 `get_version()` 函数，从 pyproject.toml 读取
- 兼容旧代码: `from config import VERSION`

### 递增逻辑 (build.sh)
1. 从 pyproject.toml 提取当前版本号 (使用 grep)
2. 构建成功后递增最后两位数字
3. 写回 pyproject.toml

## 托盘菜单修改

### 修改文件
- `ui/tray.py`

### 变更
1. 移除分隔线菜单项 (原第 74 行): `pystray.MenuItem("─", ...)`
2. 在菜单末尾添加版本号显示项 (enabled=False，不可点击)
3. 导入 VERSION: `from config import VERSION`

### 菜单结构
```
⏱ 剩余时间
🔒 立即锁屏
✓/✗ 开机启动
🚪 退出
版本号 1.7.00
```

## 实现顺序

1. 修改 `pyproject.toml` 添加 version = "1.7.00"
2. 修改 `config.py` 添加 get_version() 函数
3. 修改 `ui/tray.py` 移除分隔线、添加版本号菜单项
4. 修改 `build.sh` 添加版本读取和递增逻辑
