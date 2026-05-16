"""
macOS multiprocessing.Value patch
在Kohya训练前patch multiprocessing.Value，避免macOS沙箱权限问题
"""
import multiprocessing

# 保存原始实现
_original_Value = multiprocessing.Value

def _patched_Value(typecode_or_type, *args, **kwargs):
    """
    在macOS沙箱中，multiprocessing.Value创建共享内存锁会失败。
    在Celery solo模式下（单线程），使用普通变量即可。
    """
    try:
        return _original_Value(typecode_or_type, *args, **kwargs)
    except PermissionError:
        # 创建简单的替代品
        class SimpleValue:
            __slots__ = ['_value']
            def __init__(self, val):
                self._value = val
            @property
            def value(self):
                return self._value
            @value.setter
            def value(self, val):
                self._value = val
        
        # 根据typecode确定初始值
        if isinstance(typecode_or_type, str):
            initial = 0 if typecode_or_type in ('i', 'l', 'q') else 0.0
        else:
            initial = 0
        
        return SimpleValue(initial)

# 应用patch
multiprocessing.Value = _patched_Value
multiprocessing.RawValue = _patched_Value
