"""
The scoped symbol table is intended to be used by the Semantic Analyser module.
An 'end-to-end' use case example will be included in the tests for the Semantic Analyser
ToDo update working when adding semantic analyser tests
"""

import pytest

from shipyard.passes.semantic_analysis import scoped_symbol_table as sst
from shipyard.passes.semantic_analysis import symbols

SYMBOL_LISTS = [sst.BUILTIN_TYPES, sst.BUILTIN_ZI_EXP]
CAL_SYMBOL_LISTS = [sst.BUILTIN_CAL_TYPES, sst.BUILTIN_OPENPULSE, sst.BUILTIN_ZI_WFM]


@pytest.fixture(name="main_table")
def fixture_main_table() -> sst.ScopedSymbolTable:
    """Fixture for creating the 'main' ScopedSymbolTable
    this table has no enclosing scope

    Returns:
        sst.ScopedSymbolTable: symbol table with no enclosing scope
    """
    return sst.ScopedSymbolTable("main")


@pytest.fixture(name="nested_table")
def fixture_nested_table(main_table: sst.ScopedSymbolTable) -> sst.ScopedSymbolTable:
    """Fixture for creating a nested ScopedSymbolTable
    the 'main' symbol table encloses this table

    Args:
        main_table (sst.ScopedSymbolTable): used as enclosing scope for this table

    Returns:
        sst.ScopedSymbolTable: symbol table with enclosing scope
    """
    return sst.ScopedSymbolTable("nested", enclosing_scope=main_table)


@pytest.fixture(name="cal_table")
def fixture_cal_table(main_table: sst.ScopedSymbolTable) -> sst.CalScopedSymbolTable:
    """
    Fixture for creating 'main' a ScopedSymbolTable for openPulse code,
    has the 'main' symbol table as an enclosing scope and is initialised with
    init_cal set to True

    Args:
        main_table (sst.ScopedSymbolTable): used as enclosing scope for this table

    Returns:
        sst.CalScopedSymbolTable: main calibration symbol table
    """
    return sst.CalScopedSymbolTable("cal", enclosing_scope=main_table, init_cal=True)


@pytest.fixture(name="defcal_table")
def fixture_defcal_table(
    cal_table: sst.CalScopedSymbolTable,
) -> sst.CalScopedSymbolTable:
    """
    Fixture for creating a nested ScopedSymbolTable for openPulse code,
    has the 'main calibration' (cal_table) as an enclosing scope

    Args:
        cal_table (sst.CalScopedSymbolTable): used as enclosing scope for this table

    Returns:
        sst.CalScopedSymbolTable: nested calibration symbol table
    """
    return sst.CalScopedSymbolTable("defcal", enclosing_scope=cal_table)


def test_scoped_symbol_table_basic(main_table: sst.ScopedSymbolTable):
    """Test basic insertion and lookup in table without enclosing scope"""
    # test that built in symbols have been inserted
    for symbol_list in SYMBOL_LISTS:
        symbol_names = []
        for symbol in symbol_list:
            assert main_table.lookup(symbol.name) is symbol
            symbol_names.append(symbol.name)
        # test that names of builtin symbols are returned by the keys method
        for name in symbol_names:
            assert name in main_table.keys()
            assert name in main_table.keys(current_scope_only=True)

    # test inserting a symbol and lookin it up and name being returned by keys()
    c_symbol = symbols.ClassicalSymbol(name="test", kind=symbols.angle_type.name)
    main_table.insert(c_symbol)
    assert main_table.lookup("test") is c_symbol
    assert "test" in main_table.keys()

    # test looking up symbol that has not been inserted
    assert main_table.lookup("not_inserted") is None
    assert "not_inserted" not in main_table.keys()


@pytest.mark.parametrize("symbol_list", SYMBOL_LISTS)
def test_scoped_symbol_table_nested_built_in(
    nested_table: sst.ScopedSymbolTable, symbol_list: list[symbols.Symbol]
):
    """Test basic insertion and lookup in table with ensclosing scope"""
    # test that built in symbols are found when looking in all scopes
    # but not when only looking in current scope
    symbol_names = []
    for symbol in symbol_list:
        assert nested_table.lookup(symbol.name) is symbol
        assert nested_table.lookup(symbol.name, current_scope_only=True) is None
        symbol_names.append(symbol.name)
    for name in symbol_names:
        # test that names of built in symbols are returned by the keys method
        assert name in nested_table.keys()
        # but not when looking through only the nested scope
        assert name not in nested_table.keys(current_scope_only=True)


def test_scoped_symbol_table_nested(nested_table: sst.ScopedSymbolTable):
    # test inserting a symbol and lookin it up
    c_symbol = symbols.ClassicalSymbol(name="test", kind=symbols.angle_type.name)
    nested_table.insert(c_symbol)
    assert nested_table.lookup("test") is c_symbol
    assert nested_table.lookup("test", current_scope_only=True) is c_symbol
    # name of inserted symbol is returned by keys()
    assert "test" in nested_table.keys()
    assert "test" in nested_table.keys(current_scope_only=True)

    # test inserted symbol is not in enclosed scope, nor its name in keys
    assert nested_table.enclosing_scope.lookup("test") is None
    assert "test" not in nested_table.enclosing_scope.keys()


def test_nested_precedence(nested_table: sst.ScopedSymbolTable):
    """Test that symbols with same name can be inserted into different tables
    (one enclosed in the other) without interference with one another"""
    # create two symbols with the same name,
    # insert one into the main scope
    # insert the other into the nested scope
    #
    # when looking up the symbol in the nested scope
    # the symbol inserted into the nested scope should be returned
    c_symbol_n = symbols.ClassicalSymbol(name="test", kind=symbols.angle_type.name)
    c_symbol_m = symbols.ClassicalSymbol(name="test", kind=symbols.float_type.name)

    nested_table.enclosing_scope.insert(c_symbol_m)
    assert nested_table.lookup("test") is c_symbol_m
    nested_table.insert(c_symbol_n)
    assert nested_table.lookup("test") is c_symbol_n
    assert nested_table.enclosing_scope.lookup("test") is c_symbol_m


def test_scoped_symbol_table_string_representation(nested_table: sst.ScopedSymbolTable):
    """
    Test that the string representation of the table runs
    a more thorough test would test the actual output
    but the string representation is just used for debugging
    """
    str(nested_table)


@pytest.mark.parametrize("symbol_list", CAL_SYMBOL_LISTS)
def test_cal_table(
    cal_table: sst.CalScopedSymbolTable, symbol_list: list[symbols.Symbol]
):
    """test looking up the builtin cal symbols in the main calibration table"""
    # test that built in symbols have been inserted
    for symbol in symbol_list:
        assert cal_table.lookup(symbol.name) is symbol


@pytest.mark.parametrize("symbol_list", CAL_SYMBOL_LISTS)
def test_defcal_table(
    defcal_table: sst.CalScopedSymbolTable, symbol_list: list[symbols.Symbol]
):
    """Test looking up the builtin cal symbols in a nested calibration table"""
    # test that built in symbols have been inserted
    for symbol in symbol_list:
        assert defcal_table.lookup(symbol.name) is symbol
        assert defcal_table.lookup(symbol.name, current_scope_only=True) is None
