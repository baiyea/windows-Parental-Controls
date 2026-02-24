"""platform package - 平台相关功能"""
from .single_instance import SingleInstance
from .startup import (
    get_exe_path,
    is_in_startup,
    add_to_startup,
    remove_from_startup,
    toggle_startup,
)

__all__ = [
    'SingleInstance',
    'get_exe_path',
    'is_in_startup',
    'add_to_startup',
    'remove_from_startup',
    'toggle_startup',
]
