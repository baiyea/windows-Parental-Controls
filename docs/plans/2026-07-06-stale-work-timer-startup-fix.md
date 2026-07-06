# 启动即锁屏问题修复记录

## 问题

程序启动时会读取配置中的 `work_end_time`。如果该值早于当前时间，旧逻辑会直接进入锁屏。

当电脑重启或配置里残留很久以前的 `work_end_time` 时，程序会在启动后立即锁屏，即使这不是一次刚到休息时间后的重启。

## 处理方式

保留刚过期工作计时的锁屏行为，避免用户通过重启绕过休息。

新增陈旧计时判断：

- `work_end_time` 已过期，但过期时间不超过 `break_minutes`：启动时进入锁屏。
- `work_end_time` 已过期，且过期时间超过 `break_minutes`：视为陈旧运行状态，清除后正常进入工作计时。

## 验证

- 新增单元测试覆盖陈旧 `work_end_time` 启动后正常进入工作状态。
- 保留原有“刚过期启动进入锁屏”的测试。
- 运行 `uv run python -m unittest discover -s tests -v`。
- 运行 `uv run ruff check .`。
