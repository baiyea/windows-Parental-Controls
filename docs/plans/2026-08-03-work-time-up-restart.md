# 工作时间到点锁屏后重启实现记录

## 目标

工作/学习时间到点后，程序先进入锁屏并写入休息结束时间，再安排 3 分钟后重启计算机。重启后程序读取 `break_end_time`，继续剩余休息时间，避免通过重启刷新使用时间。

## 处理方式

- 新增配置 `auto_restart_on_work_time_up`，默认开启。
- 新增配置 `auto_restart_delay_seconds`，默认 180 秒。
- 保留旧配置 `auto_restart_after_lock`，继续表示任何锁屏后都重启。
- `monitor_loop` 触发 `WORK_TIME_UP` 时传入 `work_time_up=True`。
- `_lock_screen()` 在保存 `break_end_time`、启动锁屏窗口和播放提醒后，判断是否安排延迟重启。
- 离开锁屏或程序退出时，如果本进程安排过重启，则执行 `shutdown /a` 取消计划重启。
- debug 模式下不执行真实重启。
- 补充 `WORKING -> LOCKED` 的 `WORK_TIME_UP` 转换，避免没有进入提醒阶段时到点事件无效。

## 验证

- 测试工作时间到点后会先写入 `break_end_time`，再调用 `shutdown /r /t 180 /f`。
- 测试离开锁屏会调用 `shutdown /a` 取消计划重启。
- 测试手动锁屏不会触发到点重启。
- 测试 debug 模式不会真实重启。
