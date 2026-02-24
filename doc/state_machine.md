# 状态机设计文档

## 概述

家长控制程序现在使用状态机来管理应用程序的状态转换，使代码更加清晰、可维护和可测试。

## 状态定义

程序有以下5个状态：

```
IDLE (空闲)
  ↓ START
WORKING (工作中)
  ↓ REMIND_TIME
REMINDING (提醒阶段)
  ↓ WORK_TIME_UP
LOCKED (锁屏中)
  ↓ BREAK_TIME_UP / PASSWORD_UNLOCK
WORKING (工作中)
  ...循环
```

### 状态说明

- **IDLE**: 程序刚启动的初始状态
- **WORKING**: 正常工作计时中，用户可以使用电脑
- **REMINDING**: 即将锁屏的提醒阶段（默认提前5分钟）
- **LOCKED**: 锁屏状态，强制休息
- **EXITING**: 程序退出中

## 事件定义

触发状态转换的事件：

- **START**: 启动程序
- **REMIND_TIME**: 到达提醒时间
- **WORK_TIME_UP**: 工作时间到
- **BREAK_TIME_UP**: 休息时间到
- **PASSWORD_UNLOCK**: 密码解锁
- **FORCE_LOCK**: 强制锁屏（用户手动触发）
- **EXIT**: 退出程序
- **RESTORE_STATE**: 恢复状态（程序重启后）

## 状态转换规则

### 正常流程

1. **IDLE → WORKING** (START)
   - 触发条件：程序启动
   - 动作：开始工作计时

2. **WORKING → REMINDING** (REMIND_TIME)
   - 触发条件：距离锁屏还剩N分钟（配置中的 remind_before_minutes）
   - 动作：显示系统通知和播放音效

3. **REMINDING → LOCKED** (WORK_TIME_UP)
   - 触发条件：工作时间到
   - 动作：显示锁屏窗口

4. **LOCKED → WORKING** (BREAK_TIME_UP)
   - 触发条件：休息时间到
   - 动作：自动解锁，重新开始工作计时

### 特殊流程

5. **LOCKED → WORKING** (PASSWORD_UNLOCK)
   - 触发条件：用户输入正确密码
   - 动作：解锁，重新开始工作计时

6. **WORKING/REMINDING → LOCKED** (FORCE_LOCK)
   - 触发条件：用户点击托盘菜单"立即锁屏"
   - 动作：立即锁屏
   - 守卫条件：不在锁屏状态

7. **IDLE → LOCKED** (RESTORE_STATE)
   - 触发条件：程序重启时检测到未完成的锁屏期间
   - 动作：恢复锁屏窗口
   - 守卫条件：has_lock_state=True

8. **任意状态 → EXITING** (EXIT)
   - 触发条件：用户退出程序
   - 动作：清理资源
   - 守卫条件：不在强制休息期间

## 状态进入/退出动作

### 进入动作 (Entry Actions)

- **进入 WORKING**: 重置提醒标志
- **进入 REMINDING**: 设置提醒已显示标志
- **进入 LOCKED**: 记录日志

### 退出动作 (Exit Actions)

- **离开 WORKING**: 取消定时器
- **离开 LOCKED**: 清除锁屏结束时间配置

## 守卫条件 (Guards)

守卫条件用于控制状态转换是否允许发生：

1. **恢复锁屏守卫**: 只有当 has_lock_state=True 时才允许恢复锁屏
2. **退出守卫**: 只有不在强制休息期间才允许退出

## 线程安全

状态机使用 `threading.RLock()` 保证线程安全，所有状态转换都是原子操作。

## 状态历史

状态机会记录所有状态转换的历史，格式为：
```python
[(datetime, state), (datetime, state), ...]
```

这对于调试和追踪问题非常有用。

## 使用示例

```python
# 创建状态机
state_machine = StateMachine(AppState.IDLE)

# 配置转换规则
state_machine.add_transition(StateTransition(
    from_state=AppState.IDLE,
    event=AppEvent.START,
    to_state=AppState.WORKING,
    action=self._start_work_timer
))

# 触发事件
state_machine.trigger(AppEvent.START)

# 检查当前状态
if state_machine.is_in_state(AppState.WORKING):
    print("正在工作中")

# 获取当前状态
current_state = state_machine.get_state()
```

## 优势

1. **清晰的状态管理**: 所有状态和转换规则集中定义
2. **线程安全**: 使用锁保护状态转换
3. **可测试性**: 可以单独测试每个状态转换
4. **可扩展性**: 添加新状态或转换规则很容易
5. **调试友好**: 状态历史记录便于追踪问题
6. **守卫条件**: 灵活控制转换是否允许发生
7. **解耦**: 业务逻辑与状态管理分离

## 日志输出

状态机会输出详细的日志信息：

```
INFO:core.state_machine:状态转换: AppState.IDLE -> AppState.WORKING (事件: AppEvent.START)
INFO:core.controller:进入工作状态
INFO:core.controller:工作计时开始，结束时间: 17:30:00
```

这些日志帮助理解程序的运行状态和问题排查。
