from pathlib import Path

import pytest
from openpulse import ast, parse

from shipyard.passes.shots_extractor import ShotsExtractor


def load_ast(file: str) -> ast.Program:
    path = Path(__file__).parent.parent / f"qasm/shots_extractor/{file}.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    return parse(qasm_code)


def test_using_array(file="using_array"):
    extractor_obj = ShotsExtractor()
    extractor_obj.visit(load_ast(file))
    sig = extractor_obj.create_signature()
    assert sig.shots == 2
    assert sig.steps == [5, 6, 7, 8]


def test_using_int(file="using_int"):
    extractor_obj = ShotsExtractor()
    extractor_obj.visit(load_ast(file))
    sig = extractor_obj.create_signature()
    assert sig.shots == 2
    assert sig.steps == [5]


def test_no_shots(file="no_shots"):
    extractor_obj = ShotsExtractor()
    extractor_obj.visit(load_ast(file))
    sig = extractor_obj.create_signature()
    assert sig.shots == 1
    assert sig.steps == [3, 6, 9]


def test_no_steps(file="no_steps"):
    extractor_obj = ShotsExtractor()
    extractor_obj.visit(load_ast(file))
    sig = extractor_obj.create_signature()
    assert sig.shots == 500
    assert sig.steps == [1]


def test_no_shots_no_steps(file="no_shots_no_steps"):
    extractor_obj = ShotsExtractor()
    extractor_obj.visit(load_ast(file))
    sig = extractor_obj.create_signature()
    assert sig.shots == 1
    assert sig.steps == [1]


def test_not_arraytype(file="not_arraytype"):
    with pytest.raises(TypeError):
        extractor_obj = ShotsExtractor()
        extractor_obj.visit(load_ast(file))
