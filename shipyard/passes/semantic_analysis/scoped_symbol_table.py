"""
Module for creating scoped symbol tables
These are used during semantic analysis of openQASM code
"""

# from openpulse import ast

from ...logger import LOGGER
from .builtin_functions import (
    BUILTIN_OPENPULSE,
    BUILTIN_ZI_EXP,
    BUILTIN_ZI_FUNC,
    BUILTIN_ZI_WFM,
)
from .symbols import BUILTIN_CAL_TYPES, BUILTIN_TYPES, Symbol


class ScopedSymbolTable:
    """
    Symbol Table for keeping track of symbols, defined in openQASM programs,
    and their scope.

    Used during Semantic Analysis of openQASM programs

    The symbol table is a managed dictionary, which should not be interacted with
    directly but rather using the 'insert' and 'lookup' methods of the class.

    Todo consider implementing __getitem__, __setitem__, items() and values() methods
    """

    _builtin_symbol_lists = [BUILTIN_TYPES, BUILTIN_ZI_EXP, BUILTIN_ZI_FUNC]

    _builtin_functions = []
    _builtin_gates = ["measure"]  # todo is this built in?

    def __init__(
        self,
        scope_name: str,
        enclosing_scope: "ScopedSymbolTable" = None,
    ) -> None:
        self._symbols: dict[str, Symbol] = {}
        self.scope_name = scope_name
        self.enclosing_scope: "ScopedSymbolTable" = enclosing_scope
        LOGGER.debug("Created scope named: %s", self.scope_name)
        if enclosing_scope is None:
            self._init_builtins()

    def _init_builtins(self):
        for symbol_list in self._builtin_symbol_lists:
            for symbol in symbol_list:
                self.insert(symbol)

    def __str__(self) -> str:
        header1 = "SCOPE (SCOPED SYMBOL TABLE)"
        lines = ["\n", header1, "=" * len(header1)]
        for header_name, header_value in (
            ("Scope name", self.scope_name),
            (
                "Enclosing scope",
                self.enclosing_scope.scope_name if self.enclosing_scope else None,
            ),
        ):
            lines.append(f"{header_name:<16}: {header_value}")
        header2 = "Scope (Scoped symbol table) contents"
        lines.extend([header2, "-" * len(header2)])
        lines.extend(
            f"{key:>16}: {value.__repr__()}" for key, value in self._symbols.items()
        )
        lines.append("\n")
        symbol_table_string = "\n".join(lines)
        return symbol_table_string

    __repr__ = __str__

    def insert(self, symbol: Symbol):
        """Inserts a symbol into the symbol table

        Args:
            symbol (Symbol): Symbol to insert into the table
        """
        LOGGER.debug("Insert into %s: %s", self.scope_name, symbol)
        self._symbols[symbol.name] = symbol

    def lookup(self, name: str, current_scope_only: bool = False) -> Symbol:
        """looks up a symbol by name in the symbol table

        Args:
            name
                (str): the name of the symbol to look up in the symbol table
            current_scope_only (bool, optional):
                If True a symbol is only looked up in the current scope.
                Else, if it is not found within the current symbol table,
                it is looked up in any enclosing scopes

        Returns:
            Symbol:
                A Symbol with name matching the name being looked up,
            None:
                If a symbol with the name is not found
        """
        LOGGER.debug("Lookup: %s. (Scope name: %s", name, self.scope_name)
        # 'symbol' is either an instance of the Symbol class or None
        symbol = self._symbols.get(name, None)

        if symbol is not None:
            return symbol

        if current_scope_only:
            return None

        # recursively go up the chain and lookup the name
        if self.enclosing_scope is not None:
            return self.enclosing_scope.lookup(name)
        return None

    def keys(self, current_scope_only=False) -> list[str]:
        """returns the name of all symbols in scope

        Args:
            current_scope_only (bool, optional):
                If true only returns the names of symbols in current scope.
                Defaults to False.

        Returns:
            list[str]: names of all the symbols in scope
        """
        symbol_names = list(self._symbols.keys())
        if current_scope_only:
            return symbol_names
        if self.enclosing_scope is not None:
            symbol_names.extend(
                [
                    name
                    for name in self.enclosing_scope.keys()
                    if name not in symbol_names
                ]
            )
        return symbol_names


class CalScopedSymbolTable(ScopedSymbolTable):
    """
    Scoped Symbol Table for openPulse code, used when in 'cal' and 'defcal' blocks
    in openQASM programs and using the openPulse defcalgrammar
    """

    _builtin_cal_symbol_lists = [BUILTIN_CAL_TYPES, BUILTIN_OPENPULSE, BUILTIN_ZI_WFM]

    def __init__(
        self,
        scope_name: str,
        enclosing_scope: "ScopedSymbolTable" = None,
        init_cal: bool = False,
    ) -> None:
        super().__init__(scope_name, enclosing_scope)
        if init_cal:
            self._init_cal_builtins()

    def _init_cal_builtins(self):
        for symbol_list in self._builtin_cal_symbol_lists:
            for symbol in symbol_list:
                self.insert(symbol)
