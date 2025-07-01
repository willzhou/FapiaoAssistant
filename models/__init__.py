# models/__init__.py
from .invoice import *

__all__ = ["Invoice"]  # 控制 `from models import *` 时的行为
