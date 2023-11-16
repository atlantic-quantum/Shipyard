"""Test symbols
"""
import pytest
from pydantic import ValidationError

from shipyard.passes.semantic_analysis import symbols


@pytest.fixture(name="params")
def fixture_params() -> list[symbols.Symbol]:
    """Test fixture that is a short list of Symbols"""
    return [
        symbols.ClassicalSymbol(name="arg1", kind=symbols.angle_type.name),
        symbols.QuantumSymbol(name="arg2", kind=symbols.qubit_type.name),
    ]


def test_symbols():
    """Test creating symbols both with and without 'kind'"""
    sym1 = symbols.Symbol(name="name_test")
    assert sym1.name == "name_test"
    assert sym1.kind is None

    sym2 = symbols.Symbol(name="kind_test", kind="not_none")
    assert sym2.name == "kind_test"
    assert sym2.kind == "NOT_NONE"


builtin_symbol_names = [
    "ANGLE",
    "ARRAY",
    "BIT",
    "BITSTRING",
    "BOOL",
    "COMPLEX",
    "DURATION",
    "FLOAT",
    "IMAGINARY",
    "INT",
    "STRETCH",
    "UINT",
    "QUBIT",
]
builtin_symbols = [
    symbols.angle_type,
    symbols.array_type,
    symbols.bit_type,
    symbols.bitstring_type,
    symbols.bool_type,
    symbols.complex_type,
    symbols.duration_type,
    symbols.float_type,
    symbols.imaginary_type,
    symbols.int_type,
    symbols.stretch_type,
    symbols.uint_type,
    symbols.qubit_type,
]


@pytest.mark.parametrize(
    "symbol, name",
    [(symbol, name) for (symbol, name) in zip(builtin_symbols, builtin_symbol_names)],
)
def test_builtin_symbols(symbol: symbols.Symbol, name: str):
    """Test built in symbols have expected names and kinds"""
    assert symbol.name == name
    assert symbol.kind is None


def test_builtin_symbols_error():
    """Test error handling of built in symbols"""

    with pytest.raises(ValidationError):
        symbols.BuiltinSymbol(name="test_error", kind="NOT_NONE")

    symbols.BuiltinSymbol(name="test_no_error", kind=None)


def test_builtin_cal_symbols():
    "Test that built in cal symbols have correct names and kinds"
    builtin_cal_symbol_names = [
        "PORT",
        "FRAME",
        "WAVEFORM",
    ]

    builtin_cal_symbols = [
        symbols.port_type,
        symbols.frame_type,
        symbols.waveform_type,
    ]

    for symbol, name in zip(builtin_cal_symbols, builtin_cal_symbol_names):
        assert symbol.name == name
        assert symbol.kind is None

    with pytest.raises(ValidationError):
        symbols.BuiltinCalSymbol(name="test", kind="NOT_NONE")

    symbols.BuiltinCalSymbol(name="test_no_error", kind=None)


def test_classical_symbol():
    """Test Creating a ClassicalSymbol"""
    angle_symbol = symbols.ClassicalSymbol(
        name="angle_symbol", kind=symbols.angle_type.name
    )
    assert angle_symbol.name == "angle_symbol"
    assert angle_symbol.kind == "ANGLE"

    with pytest.raises(ValidationError):
        symbols.ClassicalSymbol(name="test_error", kind=symbols.qubit_type.name)


def test_quantum_symbol():
    """Test Creating a QuantumSymbol"""
    q_symbol = symbols.QuantumSymbol(name="q_symbol", kind=symbols.qubit_type.name)
    assert q_symbol.name == "q_symbol"
    assert q_symbol.kind == "QUBIT"

    with pytest.raises(ValidationError):
        symbols.QuantumSymbol(name="test_error", kind=symbols.angle_type.name)


def test_subroutine_symbol(params: list[symbols.Symbol]):
    """Test Creating a SubroutineSymbol"""
    sub_symbol = symbols.SubroutineSymbol(
        name="test_subroutine", params=params, return_type=symbols.bit_type.name
    )
    assert sub_symbol.name == "test_subroutine"
    assert sub_symbol.kind is None
    assert len(sub_symbol.params) == 2
    assert sub_symbol.return_type == symbols.bit_type.name

    with pytest.raises(ValidationError):
        sub_symbol = symbols.SubroutineSymbol(
            name="test_error", params=params, return_type="QUBIT"
        )


def test_gate_symbol(params: list[symbols.Symbol]):
    """Test creating a GateSymbol"""
    gate_symbol = symbols.GateSymbol(
        name="test_no_error",
        params=params,
        return_type=None,
        qubits=[symbols.QuantumSymbol(name="qubit", kind=symbols.qubit_type.name)],
    )

    assert gate_symbol.name == "test_no_error"
    assert gate_symbol.qubits[0].name == "qubit"
    assert gate_symbol.return_type is None

    with pytest.raises(ValidationError):
        symbols.GateSymbol(
            name="test_error",
            params=params,
            return_type=None,
            qubits=[
                symbols.ClassicalSymbol(name="not_qubit", kind=symbols.angle_type.name)
            ],
        )


def test_array_symbol():
    """Test creating an ArraySymbol"""
    array_symbol = symbols.ArraySymbol(
        name="test_array", kind="ARRAY", dimension=[10], base_type="FLOAT"
    )

    assert array_symbol.name == "test_array"
    assert array_symbol.kind == "ARRAY"
    assert array_symbol.base_type == "FLOAT"
    assert array_symbol.dimension == [10]

    with pytest.raises(ValidationError):
        symbols.ArraySymbol(
            name="test_error", kind="not_array", dimension=[10], base_type="FLOAT"
        )

    with pytest.raises(ValidationError):
        symbols.ArraySymbol(
            name="test_error", kind="ARRAY", dimension=[10], base_type="QUBIT"
        )
