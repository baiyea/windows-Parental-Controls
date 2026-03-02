# 夜间限制功能设计

## 需求背景

在锁屏后，如果是晚上9点之后，就不再进行休息倒计时，只能通过密码解锁。解锁后立即重新开始30分钟工作计时，如果再次锁屏还是同样的逻辑。

## 设计方案

### 配置项设计

在 `config.json` 中添加：

```json
{
  "restrict_night_hours": {
    "enabled": true,
    "start_hour": 21,
    "end_hour": 6
  }
}
```

- `enabled`: 是否启用夜间限制
- `start_hour`: 夜间限制开始时间（24小时制）
- `end_hour`: 夜间限制结束时间（次日）

### 核心逻辑

在锁屏时检查当前时间：

```python
def should_skip_break_countdown():
    """判断是否应该跳过休息倒计时"""
    current_hour = datetime.now().hour

    # 如果结束时间大于开始时间（如 21:00 到 23:00）
    if config.restrict_night_hours.end_hour > config.restrict_night_hours.start_hour:
        return config.restrict_night_hours.start_hour <= current_hour < config.restrict_night_hours.end_hour
    # 如果结束时间小于开始时间（如 21:00 到次日 6:00）
    else:
        return current_hour >= config.restrict_night_hours.start_hour or current_hour < config.restrict_night_hours.end_hour
```

### 状态机设计

在 `StateMachine` 中增加夜间限制标记：

- `is_night_restricted`: 当前是否处于夜间限制模式

### 流程变更

```
工作计时 → 锁屏 → 检查是否在夜间限制时段
                      │
            ┌─────────┴─────────┐
            │                   │
        非夜间限制            夜间限制
            │                   │
      休息倒计时30分钟      跳过倒计时
            │                   │
         自动解锁           只能密码解锁
            │                   │
            └─────────┬─────────┘
                      │
                重新工作计时
```

### UI 提示

夜间限制时，锁屏界面显示额外提示："夜间限制时段，只能密码解锁"

## 实现要点

1. 保持向后兼容，不启用时行为不变
2. 时间检查使用系统本地时间
3. 密码解锁后立即开始新的工作计时，不保留之前的剩余时间
