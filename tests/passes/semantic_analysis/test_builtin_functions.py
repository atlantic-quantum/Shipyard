"""
Minimal testing for the builtin_functions module.
just ensures that the generated list are lists of ExternSymbols.
More Rigourous testing on each function should be implemented
if we start using this module dynamically
"""
from shipyard.passes.semantic_analysis.builtin_functions import (
    BUILTIN_OPENPULSE,
    BUILTIN_ZI_EXP,
    BUILTIN_ZI_WFM,
    ExternSymbol,
)


def test_builtin_functions():
    """
    Test that the symbol lists created by the
    builtin_functions modules are lists
    of ExternSymbols
    """

    def _test_symbol_list(symbol_list: list[ExternSymbol]):
        for symbol in symbol_list:
            assert isinstance(symbol, ExternSymbol)

    symbol_lists = [
        BUILTIN_OPENPULSE,
        BUILTIN_ZI_EXP,
        BUILTIN_ZI_WFM,
    ]

    for symbol_list in symbol_lists:
        _test_symbol_list(symbol_list)
