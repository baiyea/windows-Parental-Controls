# 可信线上时间设计

## 背景

当前控制逻辑使用本地系统时间：

- `utils/night_restrict.py` 用 `datetime.now().hour` 判断夜间限制。
- `core/controller.py` 用 `datetime.now()` 计算工作结束、休息结束、提醒、退出限制和启动恢复。

如果用户修改本地时间，可以绕过夜间限制或让休息期提前结束。本次改造目标是让控制逻辑采用线上服务器时间，并在无法获得线上时间时锁屏。

## 方案

采用统一可信时间服务：

1. 新增 `utils/trusted_time.py`。
2. 使用 UDP NTP 协议请求 `ntp.aliyun.com` 和 `ntp.tencent.com`，不引入第三方依赖。
3. 同步成功后记录服务器时间和 `time.monotonic()` 基准。
4. 后续 `now()` 返回“服务器时间 + 单调时钟经过时间”，避免每秒请求 NTP，也避免本地系统时间修改影响控制逻辑。
5. 两个 NTP 服务器都不可用时，可信时间状态为不可用。

## 配置

在默认配置和 `config.json` 中增加：

```json
"trusted_time": {
    "enabled": true,
    "servers": [
        "ntp.aliyun.com",
        "ntp.tencent.com"
    ],
    "sync_interval_minutes": 10,
    "timeout_seconds": 3
}
```

## 行为

- 程序启动时先同步线上时间。
- 同步失败时立即进入锁屏，锁屏界面按夜间限制模式显示为无限期，直到能恢复可信时间或输入密码。
- 工作、休息、提醒、启动恢复、退出限制、夜间限制判断都使用可信时间。
- 监控循环中定期刷新可信时间；如果刷新失败或可信时间不可用，则进入或保持锁屏。
- 如果配置关闭 `trusted_time.enabled`，才允许回退本地时间。默认开启。

## 文件边界

- `utils/trusted_time.py`：NTP 请求、时间基准、可信时间读取。
- `utils/night_restrict.py`：只负责根据传入或可信当前时间判断是否处于夜间限制。
- `core/controller.py`：只消费可信时间，不直接使用本地时间做控制判断。
- `config.py` / `config.json`：提供默认可信时间配置。
- `tests/`：用 `unittest` 覆盖关键行为，避免引入新测试依赖。

## 错误处理

- NTP 请求超时、DNS 失败、响应太短或返回时间非法时，尝试下一个服务器。
- 所有服务器失败时抛出 `TrustedTimeUnavailable` 或返回不可用状态。
- 控制器遇到可信时间不可用时锁屏，避免断网或屏蔽 NTP 服务器绕过控制。

## 测试策略

- `trusted_time` 测试使用假的 NTP 客户端和假的单调时钟，验证成功同步、推算当前时间和失败异常。
- 夜间限制测试注入固定时间，验证跨天范围。
- 控制器测试替换可信时间提供者，验证启动同步失败会进入锁屏状态。
