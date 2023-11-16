"""
Tests of function signature name mangling and matching signatures to mangled signatures
"""

import pytest
from openpulse import ast

from shipyard.mangle import FunctionSignature, MangledSignature, Mangler


@pytest.fixture(name="f_signature")
def fixture_f_signature():
    """Fixture for creating a FunctionSignature object"""
    return FunctionSignature(
        name="my_function",
        params=["param1", "param2", "param3"],
        qubits=["$1", "$3"],
        return_type="ANGLE",
    )


@pytest.fixture(name="m_signature_string")
def fixture_m_signature_string():
    """fixture for a mangled function signature"""
    return "_ZN11my_function_PN3_param1_param2_param3_QN2_$1_$3_RANGLE"


# pylint: disable=R0913
def expected_match_answer(
    full_p_match: int,
    full_q_match: int,
    partial_p_match: int,
    partial_q_match: int,
    l_params: int,
    l_qubits: int,
) -> float:
    """Function to calculate the expected result of the MangleSignature.match method

    Args:
        full_p_match (int):
            The number of parameters in the call to the match method we expect to
            have a 1:1 relation to the parameters in the mangled signature
        full_q_match (int):
            The number of qubits in the call to the match method we expect to
            have a 1:1 relation to the qubits in the mangled signature
        partial_p_match (int):
            The number of parameters in the call to the match method we expect to
            have a partial relation to the parameters in the mangled signature,
            currently any number is treated as a partial match
            (no type checking is performed)
        partial_q_match (int):
            The number of qubits in the call to the match method we expect to
            have a partial relation to the qubits in the mangled signature,
            currently if a physical qubit is called for a signature defined with
            a wildcard qubit (no $) it is determined to be a partial match
        l_params (int):
            the number of parameters used in the call to the match method
        l_qubits (int):
            the number of qubits used in the call to the match method


    Returns:
        float:
            sum of expected full matches
            plus (partial param matches divided with the number of parameters in the
            call plus one)
            plut (partial qubit matches divided with ((the number of parameters in the
            call plus one) and (with the number of qubits in the call plus one))
            This is done so that number of full matches allways supercedes number of
            partial matches
    """
    return (
        full_p_match
        + full_q_match
        + partial_p_match / (l_params + 1)
        + partial_q_match / ((l_params + 1) * (l_qubits + 1))
    )


# pylint: enable=R0913


def test_function_signature_mangling(
    f_signature: FunctionSignature, m_signature_string: str
):
    """Test that various function signatures mangle correcly"""
    assert f_signature.mangle() == m_signature_string

    name = "my_function"
    params = ["param1", "param2", "param3"]
    qubits = ["$1", "$3"]
    return_type = "ANGLE"

    assert FunctionSignature(name=name).mangle() == "_ZN11my_function_PN0_QN0_R"
    assert (
        FunctionSignature(name=name, params=params).mangle()
        == "_ZN11my_function_PN3_param1_param2_param3_QN0_R"
    )
    assert (
        FunctionSignature(name=name, qubits=qubits).mangle()
        == "_ZN11my_function_PN0_QN2_$1_$3_R"
    )
    assert (
        FunctionSignature(name=name, return_type=return_type).mangle()
        == "_ZN11my_function_PN0_QN0_RANGLE"
    )
    assert (
        FunctionSignature(name=name, params=params, qubits=qubits).mangle()
        == "_ZN11my_function_PN3_param1_param2_param3_QN2_$1_$3_R"
    )
    assert (
        FunctionSignature(name=name, params=params, return_type=return_type).mangle()
        == "_ZN11my_function_PN3_param1_param2_param3_QN0_RANGLE"
    )
    assert (
        FunctionSignature(name=name, qubits=qubits, return_type=return_type).mangle()
        == "_ZN11my_function_PN0_QN2_$1_$3_RANGLE"
    )
    assert FunctionSignature(name="name-dash").mangle() == "_ZN9name-dash_PN0_QN0_R"
    assert (
        FunctionSignature(name=name, params=["1.5", "param2"]).mangle()
        == "_ZN11my_function_PN2_1.5_param2_QN0_R"
    )


def test_mangled_signature(m_signature_string: str):
    """Test the methods of the MangledSignature class"""
    m_signature = MangledSignature(signature=m_signature_string)
    assert m_signature.name() == "my_function"
    assert m_signature.params() == ["param1", "param2", "param3"]
    assert m_signature.qubits() == ["$1", "$3"]
    assert m_signature.return_type() == "ANGLE"
    assert str(m_signature) == m_signature_string

    mangled_signature2 = MangledSignature(signature="_ZN11my_function_PN0_QN0_R")
    assert mangled_signature2.name() == "my_function"
    assert mangled_signature2.params() == []
    assert mangled_signature2.qubits() == []
    assert mangled_signature2.return_type() == ""


def test_mangled_signture_matching_basic(f_signature: FunctionSignature):
    """Test matching a mangled function signature to parameters and qubits"""
    f_call = FunctionSignature(
        name="my_function",
        params=["1", "2", "3"],
        qubits=["$1", "$3"],
        return_type="ANGLE",
    )

    mangled_signature = MangledSignature(signature=f_signature.mangle())
    assert mangled_signature.match(
        f_call.params, f_call.qubits
    ) == expected_match_answer(0, 2, 3, 0, 3, 2)


def test_mangled_signature_matching_constant():
    """Test that matching mangled signatures to function signature parameters
    work for functions defined with constants"""
    function_signature = FunctionSignature(
        name="test_const",
        params=["1.4", "param2", "param3"],
        qubits=["$1", "q"],
        return_type="BIT",
    )

    function_call = FunctionSignature(
        name="test_const",
        params=["1.4", "2", "3"],
        qubits=["$1", "$2"],
    )

    mangled_signature = MangledSignature(signature=function_signature.mangle())
    assert mangled_signature.match(
        function_call.params, function_call.qubits
    ) == expected_match_answer(1, 1, 2, 1, 3, 2)


@pytest.fixture(name="ms_list")
def fixture_ms_list() -> list[str]:
    """Fixture for creating a list of mangled function signatures"""

    def _signature(
        param1: str = "param1",
        param2: str = "param2",
        param3: str = "param3",
        qubit1: str = "c",
        qubit2: str = "t",
    ):
        return FunctionSignature(
            name="ctrlU3", params=[param1, param2, param3], qubits=[qubit1, qubit2]
        )

    signatues = []
    signatues.append(_signature().mangle())
    signatues.append(_signature(param1="1.571").mangle())
    signatues.append(_signature(param2="2").mangle())
    signatues.append(_signature(param1="1.571", param2="2").mangle())
    signatues.append(_signature(param1="1.571", param2="2", param3="5").mangle())
    signatues.append(_signature(param1="1.571", param2="4", param3="5").mangle())
    signatues.append(
        _signature(param1="1.571", param2="4", param3="5", qubit1="$1").mangle()
    )
    signatues.append(
        _signature(
            param1="1.571", param2="4", param3="5", qubit1="$1", qubit2="$0"
        ).mangle()
    )
    signatues.append(_signature(param3="5", qubit1="$1", qubit2="$0").mangle())

    return signatues


SIGNATURES = [
    (0, {}),
    (1, {"param1": "1.571"}),
    (0, {"param1": "1.570"}),
    (0, {"param1": "1.572"}),
    (2, {"param2": "2"}),
    (3, {"param1": "1.571", "param2": "2"}),
    (2, {"param1": "1.570", "param2": "2"}),
    (2, {"param1": "1.572", "param2": "2"}),
    (4, {"param1": "1.571", "param2": "2", "param3": "5"}),
    (5, {"param1": "1.571", "param2": "4", "param3": "5"}),
    (6, {"param1": "1.571", "param2": "4", "param3": "5", "qubit1": "$1"}),
    (
        7,
        {
            "param1": "1.571",
            "param2": "4",
            "param3": "5",
            "qubit1": "$1",
            "qubit2": "$0",
        },
    ),
    (8, {"param3": "5", "qubit1": "$1", "qubit2": "$0"}),
]


@pytest.mark.parametrize("index, kwargs", SIGNATURES)
def test_function_signature_matching(ms_list, index, kwargs):
    """
    Test that different function signatures correctly
    match to mangled function signatures
    """

    # pylint: disable=R0913
    def match_signature(
        index: int,
        param1: str = "param1",
        param2: str = "param2",
        param3: str = "param3",
        qubit1: str = "r",
        qubit2: str = "q",
    ):
        function_signature = FunctionSignature(
            name="ctrlU3", params=[param1, param2, param3], qubits=[qubit1, qubit2]
        )
        assert function_signature.match(ms_list) == [ms_list[index]]

    # pylint: enable=R0913
    match_signature(index, **kwargs)


def test_mangler():
    ARGS = 4
    QBITS = 3
    id_node = ast.Identifier("id")
    arguments = [
        ast.ClassicalArgument(ast.FloatType(), ast.Identifier(f"p{i}"))
        for i in range(ARGS)
    ]
    qubits = [ast.Identifier(f"${i}") for i in range(QBITS)]
    return_node = ast.BitType()

    defcal_node = ast.CalibrationDefinition(
        id_node, arguments, qubits, return_type=return_node, body=[]
    )

    mangler = Mangler(defcal_node)

    assert mangler.name == "id"
    assert mangler.arguments == ["FLOAT" for _ in range(ARGS)]
    assert mangler.qubits == [f"${i}" for i in range(QBITS)]
    assert mangler.return_type == "BIT"

    assert (
        mangler.signature().mangle()
        == "_ZN2id_PN4_FLOAT_FLOAT_FLOAT_FLOAT_QN3_$0_$1_$2_RBIT"
    )

    call_arguments = [ast.FloatLiteral(i) for i in range(ARGS)]
    quantum_gate_call = ast.QuantumGate([], id_node, call_arguments, qubits)
    c_mangler = Mangler(quantum_gate_call)

    assert c_mangler.name == "id"
    assert c_mangler.arguments == [f"{i}" for i in range(ARGS)]
    assert c_mangler.qubits == [f"${i}" for i in range(QBITS)]
    assert c_mangler.return_type == ""


def test_mangler_quantum_measurment():
    q_meas_node = ast.QuantumMeasurement(ast.Identifier("$1"))

    mangler = Mangler(q_meas_node)

    assert mangler.name == "measure"
    assert mangler.arguments == []
    assert mangler.qubits == ["$1"]
    assert mangler.return_type == "BIT"

    assert mangler.signature().mangle() == "_ZN7measure_PN0_QN1_$1_RBIT"

    with pytest.raises(NotImplementedError):
        Mangler(
            ast.QuantumReset(
                ast.IndexedIdentifier(ast.Identifier("q"), [ast.IntegerLiteral(1)])
            )
        )

    with pytest.raises(NotImplementedError):
        Mangler().visit_QuantumReset(None)


def test_mangler_quantum_reset():
    q_reset_node = ast.QuantumReset(ast.Identifier("$1"))

    mangler = Mangler(q_reset_node)

    assert mangler.name == "reset"
    assert mangler.arguments == []
    assert mangler.qubits == ["$1"]
    assert mangler.return_type == ""

    assert mangler.signature().mangle() == "_ZN5reset_PN0_QN1_$1_R"

    with pytest.raises(NotImplementedError):
        Mangler(
            ast.QuantumMeasurement(
                ast.IndexedIdentifier(ast.Identifier("q"), [ast.IntegerLiteral(1)])
            )
        )

    with pytest.raises(NotImplementedError):
        Mangler().visit_QuantumMeasurement(None)
