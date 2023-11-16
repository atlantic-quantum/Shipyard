"""
Definitions of instrument types and their cores as Literal types.
and a dictionary mapping instrument types to a
list of tuples of core counts and core types.
"""
from typing import Literal

InstrumentType = Literal[
    "HDAWG8",
    "HDAWG4",
    "SHFSG8",
    "SHFSG4",
    "SHFQA4",
    "SHFQA2",
    "SHFQC6",
    "SHFQC4",
    "SHFQC2",
    "SHFQC",
    "PQSC",
]

CoreType = Literal["HD", "QA", "SG"]

instrument_type_info: dict[str, list[tuple[int, CoreType]]] = {
    "HDAWG8": [(4, "HD")],
    "HDAWG4": [(2, "HD")],
    "SHFSG8": [(8, "SG")],
    "SHFSG4": [(4, "SG")],
    "SHFQA4": [(4, "QA")],
    "SHFQA2": [(2, "QA")],
    "SHFQC6": [(6, "SG"), (1, "QA")],
    "SHFQC4": [(4, "SG"), (1, "QA")],
    "SHFQC2": [(2, "SG"), (1, "QA")],
    "SHFQC": [(2, "SG"), (1, "QA")],
    "PQSC": [],
}
