# 日志系统说明

## 概述

程序已经统一使用 Python 的 logging 模块进行日志记录，所有日志会同时输出到：
1. 控制台（标准输出）
2. 日志文件：`log/年-月-日.log`（例如：`log/2026-02-24.log`）

## 日志格式

```
[时间戳] [日志级别] [模块名] 日志消息
```

示例：
```
[2026-02-24 17:35:53] [INFO] [main] 家长控制启动...
[2026-02-24 17:36:10] [WARNING] [core.controller] 锁屏期间不允许退出
[2026-02-24 17:36:25] [ERROR] [config] 保存配置失败: Permission denied
```

## 日志级别

- `DEBUG`: 调试信息（默认不显示）
- `INFO`: 普通信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息

## 使用方法

在任何模块中使用日志：

```python
from utils import get_logger

logger = get_logger(__name__)

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## 日志文件管理

- 日志文件按日期自动创建，每天一个文件
- 日志文件位置：项目根目录下的 `log/` 文件夹
- 打包成 exe 后，日志文件会在 exe 所在目录的 `log/` 文件夹中
- 建议定期清理旧的日志文件

## 初始化

在程序入口（`main.py`）中已经初始化了日志系统：

```python
from utils import setup_logger

# 初始化日志系统
setup_logger()
```

其他模块只需要使用 `get_logger()` 获取 logger 实例即可。

## 注意事项

1. 所有 `print()` 语句已经替换为 `logger` 调用
2. 日志会自动包含时间戳，无需手动添加
3. 日志文件使用 UTF-8 编码，支持中文
4. 日志目录会自动创建，无需手动创建
