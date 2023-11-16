"""
Module for handling core-level specific functionality
"""
from .awg_core import AWGCore, CoreType
from .hd_core import HDCore
from .qa_core import QACore
from .sg_core import SGCore

CORE_TYPE_TO_CLASS: dict[CoreType, AWGCore] = {
    CoreType.HD: HDCore(),
    CoreType.QA: QACore(),
    CoreType.SG: SGCore(),
}
