"""状态机模块"""
from enum import Enum, auto
from typing import Callable, Dict, Optional, Tuple
from datetime import datetime
import threading
from utils import get_logger

logger = get_logger(__name__)


class AppState(Enum):
    """应用程序状态"""
    IDLE = auto()           # 空闲状态（刚启动）
    WORKING = auto()        # 工作中（计时中）
    REMINDING = auto()      # 提醒阶段（即将锁屏）
    LOCKED = auto()         # 锁屏中（休息时间）
    EXITING = auto()        # 退出中


class AppEvent(Enum):
    """应用程序事件"""
    START = auto()              # 启动程序
    WORK_TIME_UP = auto()       # 工作时间到
    REMIND_TIME = auto()        # 到达提醒时间
    BREAK_TIME_UP = auto()      # 休息时间到
    PASSWORD_UNLOCK = auto()    # 密码解锁
    FORCE_LOCK = auto()         # 强制锁屏
    EXIT = auto()               # 退出
    RESTORE_STATE = auto()      # 恢复状态（重启后）


class StateTransition:
    """状态转换定义"""
    def __init__(self, from_state: AppState, event: AppEvent, 
                 to_state: AppState, action: Optional[Callable] = None,
                 guard: Optional[Callable] = None):
        self.from_state = from_state
        self.event = event
        self.to_state = to_state
        self.action = action  # 转换时执行的动作
        self.guard = guard    # 转换条件（返回 True 才能转换）


class StateMachine:
    """状态机管理器"""
    
    def __init__(self, initial_state: AppState):
        self.current_state = initial_state
        self.previous_state = None
        self.transitions: Dict[Tuple[AppState, AppEvent], StateTransition] = {}
        self.state_entry_actions: Dict[AppState, Callable] = {}
        self.state_exit_actions: Dict[AppState, Callable] = {}
        self.lock = threading.RLock()  # 线程安全
        
        # 状态历史（用于调试和恢复）
        self.state_history = [(datetime.now(), initial_state)]
        
    def add_transition(self, transition: StateTransition):
        """添加状态转换规则"""
        key = (transition.from_state, transition.event)
        self.transitions[key] = transition
        
    def add_entry_action(self, state: AppState, action: Callable):
        """添加进入状态时的动作"""
        self.state_entry_actions[state] = action
        
    def add_exit_action(self, state: AppState, action: Callable):
        """添加离开状态时的动作"""
        self.state_exit_actions[state] = action
        
    def trigger(self, event: AppEvent, **kwargs) -> bool:
        """触发事件，尝试状态转换"""
        with self.lock:
            key = (self.current_state, event)
            transition = self.transitions.get(key)
            
            if not transition:
                logger.warning(f"无效的状态转换: {self.current_state} -> {event}")
                return False
                
            # 检查转换条件
            if transition.guard and not transition.guard(**kwargs):
                logger.info(f"状态转换被阻止: {self.current_state} -> {event}")
                return False
                
            # 执行状态转换
            old_state = self.current_state
            new_state = transition.to_state
            
            logger.info(f"状态转换: {old_state} -> {new_state} (事件: {event})")
            
            # 1. 执行退出动作
            if old_state in self.state_exit_actions:
                try:
                    self.state_exit_actions[old_state](**kwargs)
                except Exception as e:
                    logger.error(f"退出动作失败: {e}")
                    
            # 2. 执行转换动作
            if transition.action:
                try:
                    transition.action(**kwargs)
                except Exception as e:
                    logger.error(f"转换动作失败: {e}")
                    
            # 3. 更新状态
            self.previous_state = old_state
            self.current_state = new_state
            self.state_history.append((datetime.now(), new_state))
            
            # 4. 执行进入动作
            if new_state in self.state_entry_actions:
                try:
                    self.state_entry_actions[new_state](**kwargs)
                except Exception as e:
                    logger.error(f"进入动作失败: {e}")
                    
            return True
            
    def get_state(self) -> AppState:
        """获取当前状态（线程安全）"""
        with self.lock:
            return self.current_state
            
    def is_in_state(self, state: AppState) -> bool:
        """检查是否处于指定状态"""
        with self.lock:
            return self.current_state == state
