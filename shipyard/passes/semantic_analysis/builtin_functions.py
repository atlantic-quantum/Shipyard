"""
Create lists of symbols from json files for builtin functions

symbols are created for

openpulse functions e.g. set/get/shift frequency of frames
zi:seqc waveform functions e.g. create a gaussian waveform at compile time
zi:seqc math expression e.g. sin, cos, tan

see json files in the '_static' folder for a complete list of all the functions

for openpulse based on
    https://openqasm.com/language/openpulse.html
for zi:seqc based on
    https://docs.zhinst.com/hdawg_user_manual/functional_description/awg.html
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field, validator

from .symbols import ClassicalSymbol, ExternSymbol


class FunctionSignature(BaseModel):
    """A pydantic model for function signatures.

    A json file containing function signatures should be of the form

    {
        function_name: {
            "inputs" : {
                "arg_1": "TYPE",
                "arg_2": "TYPE",
                ...
                "arg_n": "TYPE"
            },
            "return_type": "RETURN_TYPE"
        },
        ...
    }

    where "TYPE" strings and "RETURN_TYPE" are the names
    of builtin types in openQASM / openpulse

    if a function has no return type use 'null' instead (without quotes)
    """

    inputs: dict[str, str] = Field(default_factory=lambda: {})
    return_type: str = None

    @validator("inputs")
    def make_input_type_upper_case(cls, inputs: dict[str, str]):
        """Ensures that the type names are uppercase such that thay match
        the symbol names for built in type (see symbols.py for details)


        Args:
            input (dict[str, str]): a dictionary of input names and type names

        Returns:
            _type_: a dictionary of input names and types in the same order as the
                    input dictionary but with the type names in uppercase
        """

        return {k: v.upper() for k, v in inputs.items()}

    def to_symbol(self, function_name: str) -> ExternSymbol:
        """Converts the function signature into an ExternSymbol with name equal to
        function name, the symbol can be inserted into a symbol table.

        Args:
            function_name (str): the name the ExternSymbol will have

        Returns:
            ExternSymbol: An ExternSymbol with name function_name and params and
                          return_type determine by the FunctionSignature object
        """
        return ExternSymbol(
            name=function_name,
            params=[ClassicalSymbol(name=n, kind=k) for (n, k) in self.inputs.items()],
            return_type=self.return_type,
        )


def symbols_from_json(file: str) -> list[ExternSymbol]:
    """Creates a dictionary function signature from a json file.

    The json file should contain entries of the form FunctionSignature

    Args:
        file (str): the name of a json file in the '_static' folder that function
                    signatures will be created from

    Returns:
        list: a list of ExternSymbols created from a json file
    """

    path = Path(__file__).parent / "_static" / file
    with open(path, encoding="utf_8") as json_file:
        data = json_file.read()
    f_json = json.loads(data)
    signatures = {k: FunctionSignature(**v) for k, v in f_json.items()}
    return [v.to_symbol(k) for k, v in signatures.items()]


BUILTIN_OPENPULSE = symbols_from_json("openpulse_functions.json")
BUILTIN_ZI_WFM = symbols_from_json("zi_wfm_functions.json")
BUILTIN_ZI_EXP = symbols_from_json("zi_expressions.json")
BUILTIN_ZI_FUNC = symbols_from_json("zi_functions.json")
