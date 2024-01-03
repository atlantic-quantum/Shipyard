"""
Symbols for data types in openQASM

Based on
    https://openqasm.com/language/types.html
    https://openqasm.com/language/openpulse.html
"""

from pydantic import BaseModel, Field, validator, field_validator

_BUILTIN_CLASSICAL_SYMBOL_NAMES = [
    "ANGLE",
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
    "PORT",
    "FRAME",
    "WAVEFORM",
    "ARRAY",
]
# todo watch out for isses with handling arrays as classical types, refactor if needed.

_BUILTIN_QUANTUM_SYMBOL_NAMES = ["QUBIT"]


class Symbol(BaseModel):
    """Base class for Symbols"""

    name: str
    kind: str | None = None

    @field_validator("kind")
    def force_kind_uppercase(cls, kind: str) -> str:
        """If the string 'kind' is not None make it uppercase

        Args:
            kind (str): a string (or None)

        Returns:
            str: the same string but uppercase (returns None if 'kind' is None)
        """
        if kind is not None:
            return kind.upper()
        return kind


def kind_of_builtin_is_none(kind: str | None) -> None:
    """A function to validate that built in symbols have no kind

    Args:
        kind (str): the kind of the built in symbol, should be None

    Returns:
        str: the kind of the built in symbol
    """
    assert kind is None
    return None


class BuiltinSymbol(Symbol):
    """Builtin Symbols for openQASM should be defined using this (BuiltinSymbol) class

    Builtin Symbols have names correspond to the type that they represent
    and kind set to None

    A Builtin Symbol should be defined for the following types

    ANGLE
    BIT
    BITSTRING
    BOOL
    COMPLEX
    DURATION
    FLOAT
    IMAGINARY
    INT
    STRETCH
    UINT

    QUBIT
    """

    _validate_kind = field_validator("kind")(kind_of_builtin_is_none)


angle_type = BuiltinSymbol(name="ANGLE")
array_type = BuiltinSymbol(name="ARRAY")
bit_type = BuiltinSymbol(name="BIT")
bitstring_type = BuiltinSymbol(name="BITSTRING")
bool_type = BuiltinSymbol(name="BOOL")
complex_type = BuiltinSymbol(name="COMPLEX")
duration_type = BuiltinSymbol(name="DURATION")
float_type = BuiltinSymbol(name="FLOAT")
imaginary_type = BuiltinSymbol(name="IMAGINARY")
int_type = BuiltinSymbol(name="INT")
stretch_type = BuiltinSymbol(name="STRETCH")
uint_type = BuiltinSymbol(name="UINT")

qubit_type = BuiltinSymbol(name="QUBIT")

# todo binary, octal, decimal, hex, hardware qubit

BUILTIN_TYPES = [
    angle_type,
    array_type,
    bit_type,
    bitstring_type,
    bool_type,
    complex_type,
    duration_type,
    float_type,
    imaginary_type,
    int_type,
    qubit_type,
    stretch_type,
    uint_type,
]


class BuiltinCalSymbol(Symbol):
    """Builtin Symbols for openpulse calibration grammar should be defined using
    this (BuiltinCalSymbol) class

    Builtin Symbols have names correspond to the type that they represent
    and kind set to None

    A Builtin Calibration Symbol should be defined for the following types

    PORT
    FRAME
    WAVEFORM
    """

    _validate_kind = field_validator("kind")(kind_of_builtin_is_none)


port_type = BuiltinCalSymbol(name="PORT")
frame_type = BuiltinCalSymbol(name="FRAME")
waveform_type = BuiltinCalSymbol(name="WAVEFORM")

BUILTIN_CAL_TYPES = [
    frame_type,
    port_type,
    waveform_type,
]

_ALLOWED_ARRAY_TYPES = [
    "ANGLE",
    "BIT",
    "BOOL",
    "COMPLEX",
    "FLOAT",
    "INT",
    "UINT",
]


class ArraySymbol(Symbol):
    """A symbol that represents an array of symbols of a particular type"""

    dimension: list[int]
    base_type: str

    @field_validator("kind")
    def kind_is_array(cls, kind: str) -> str:
        """returns the input string if it is 'ARRAY' (kind of ArraySymbol is ARRAY)

        Args:
            kind (str): name of kind of ArraySymbol, should be 'ARRAY'

        Returns:
            str: 'ARRAY'
        """
        assert kind.upper() == "ARRAY"
        return kind.upper()

    @field_validator("base_type")
    def array_base_type_must_be_of_allowed_type(cls, base_type: str) -> str:
        """returns the input string if it is a valid name for an array type
        else raises assertion error (that is turned into a validation error by
        the pydantic model class)

        Args:
            kind (str): the name of the base_type of the array

        Returns:
            str: if the input string is a name of an allowed array base type
                 it is returned
        """
        assert base_type in _ALLOWED_ARRAY_TYPES
        return base_type


class AliasSymbol(Symbol):
    """A symbol that represents an alias of another symbol"""


def kind_must_be_name_of_classical_type(kind: str) -> str:
    """returns the input string if it is a valid name for a built in symbol
    else raises assertion error (that is turned into a validation error by
    the pydantic model class)

    Args:
        kind (str): the name of the kind a Classical type

    Returns:
        str: if the input string is a name of a Classical type then it is returned
    """
    assert kind in _BUILTIN_CLASSICAL_SYMBOL_NAMES
    return kind


class ClassicalSymbol(Symbol):
    """A symbol that represents a classical variable

    the kind of the symbol should be the name of a builtin classical symbol
    (i.e. BuiltinSymbol/BuiltinCalSymbol but not QUBIT)
    """

    _validate_classical = field_validator("kind")(
        kind_must_be_name_of_classical_type
    )


class LiteralSymbol(ClassicalSymbol):
    """A symbol that represents a Literal"""


class ConstantSymbol(Symbol):
    """A symbol that represents a classical compile time constant

    the kind of the symbol should be the name of a builtin classical symbol
    (i.e. BuiltinSymbol/BuiltinCalSymbol but not QUBIT)
    """

    _validate_classical = field_validator("kind")(
        kind_must_be_name_of_classical_type
    )


class IOSymbol(Symbol):
    """A symbol that represents Input/Output of a script,
    i.e. a value that will be provided at runtime or a value that will be returned
    from running the script.

    This behaviour is not currently implemented in our pipeline

    for further reading
    https://openqasm.com/language/directives.html#input-output
    """

    _validate_classical = field_validator("kind")(
        kind_must_be_name_of_classical_type
    )


class QuantumSymbol(Symbol):
    """
    A symbol representing quantum objects, i.e., either a qubit or a qubit register
    """

    @field_validator("kind")
    def kind_must_be_name_of_quantum_type(cls, kind: str) -> str:
        """if the input string is a name of a quantum type it is returned else a
        validation error is raised

        Args:
            kind (str): should be the name of a quantum type

        Returns:
            str: input string if it is a name of a quantum type
        """
        assert kind in _BUILTIN_QUANTUM_SYMBOL_NAMES
        return kind


class GrammarSymbol(Symbol):
    """A symbol representing the pulse grammar used by the script,

    currently, if used, shoul have a value of openpulse
    """


class SubroutineSymbol(Symbol):
    """A symbol representing subroutines

    for further reading
    https://openqasm.com/language/subroutines.html
    """

    params: list[Symbol] = Field(default_factory=lambda: [])
    return_type: str | None = None

    @field_validator("return_type")
    def return_classical_or_none(cls, return_type: str):
        """If the return type is a classical type or an array it is returned
        in upper case format, else a ValidationError is raised

        Args:
            return_type (str): should be a name of a valid classical type or 'array'

        Returns:
            str: uppercase input string if valid classical type or 'ARRAY'
        """
        if return_type is not None:
            return_type = return_type.upper()
            assert return_type in _BUILTIN_CLASSICAL_SYMBOL_NAMES + ["ARRAY"]
        return return_type


class ExternSymbol(SubroutineSymbol):
    """A symbol representing external functions or ports,

    for further reading
    https://openqasm.com/language/classical.html#extern-function-calls
    """


class GateSymbol(SubroutineSymbol):
    """A symbol representing a quantum gate operation

    a quantum gate represents the unitary quantum operation

    for further reading
    https://openqasm.com/language/gates.html
    """

    qubits: list[QuantumSymbol] = Field(default_factory=lambda: [])


class DefcalSymbol(GateSymbol):
    """A symbol representing a calibration definition of an operation

    e.g., the physical pulses used to perfrom a gate operation
    or a measurement on a qubit

    for further reading
    https://openqasm.com/language/pulses.html
    """
