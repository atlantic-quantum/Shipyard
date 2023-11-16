import pytest
from numpy.random import rand, randint
from openpulse import ast

from shipyard.visitors.literal_visitor import LiteralVisitor
from shipyard.visitors.type_visitor import TypeVisitor


def test_literal_visitor_bitstring():
    bs_node = ast.BitstringLiteral(7, 4)
    assert LiteralVisitor().visit_BitstringLiteral(bs_node) == '"0111"'


def test_literal_visitor_int():
    for _ in range(100):
        rand_int = randint(-10000, 10000)
        int_node = ast.IntegerLiteral(rand_int)
        assert LiteralVisitor().visit_IntegerLiteral(int_node) == f"{rand_int}"


def test_literal_visitor_float():
    for _ in range(100):
        r_number = rand()
        f_node = ast.FloatLiteral(r_number)
        assert LiteralVisitor().visit_FloatLiteral(f_node) == f"{r_number}"


def test_literal_visitor_imaginary():
    for _ in range(100):
        r_number = rand()
        f_node = ast.ImaginaryLiteral(r_number)
        assert LiteralVisitor().visit_ImaginaryLiteral(f_node) == f"{r_number}im"


def test_literal_visitor_boolean():
    assert LiteralVisitor().visit_BooleanLiteral(ast.BooleanLiteral(True)) == "true"
    assert LiteralVisitor().visit_BooleanLiteral(ast.BooleanLiteral(False)) == "false"


def test_literal_visitor_duration():
    time_units = ["ns", "us", "ms", "s", "dt"]
    for time_unit in time_units:
        r_number = rand()
        d_node = ast.DurationLiteral(r_number, ast.TimeUnit[time_unit])
        assert (
            LiteralVisitor().visit_DurationLiteral(d_node) == f"{r_number}{time_unit}"
        )


def test_type_visitor_angle():
    assert TypeVisitor().visit_AngleType(ast.AngleType()) == "ANGLE"


def test_type_visitor_bit():
    assert TypeVisitor().visit_BitType(ast.BitType()) == "BIT"


def test_type_visitor_bool():
    assert TypeVisitor().visit_BoolType(ast.BoolType()) == "BOOL"


def test_type_visitor_array():
    assert (
        TypeVisitor().visit_ArrayType(
            ast.ArrayType(base_type=ast.IntType, dimensions=[])
        )
        == "ARRAY"
    )


def test_type_visitor_int():
    assert TypeVisitor().visit_IntType(ast.IntType()) == "INT"


def test_type_visitor_float():
    assert TypeVisitor().visit_FloatType(ast.FloatType()) == "FLOAT"


def test_type_visitor_uint():
    assert TypeVisitor().visit_UintType(ast.UintType()) == "UINT"


def test_type_visitor_complex():
    assert TypeVisitor().visit_ComplexType(ast.ComplexType(ast.FloatType)) == "COMPLEX"


def test_type_visitor_duration():
    assert TypeVisitor().visit_DurationType(ast.DurationType()) == "DURATION"


def test_type_visitor_stretch():
    assert TypeVisitor().visit_StretchType(ast.StretchType()) == "STRETCH"


def test_type_visitor_port():
    assert TypeVisitor().visit_PortType(ast.PortType()) == "PORT"


def test_type_visitor_frame():
    assert TypeVisitor().visit_FrameType(ast.FrameType()) == "FRAME"


def test_type_visitor_waveform():
    assert TypeVisitor().visit_WaveformType(ast.WaveformType()) == "WAVEFORM"


def test_type_visitor_array_reference():
    with pytest.raises(NotImplementedError):
        TypeVisitor().visit_ArrayReferenceType(None)
