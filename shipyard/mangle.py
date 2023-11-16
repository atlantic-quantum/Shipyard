"""
Module for mangling and demangling function signature for openQASM
"""

from openpulse import ast
from pydantic import BaseModel, Field

from .logger import LOGGER
from .utilities import is_number
from .visitors import GenericVisitor, LiteralVisitor, TypeVisitor


class MangledSignature(BaseModel):
    """
    Pydantic Model for mangled function signatures and methods for
    extracing information about the function out of the mangled signature
    """

    signature: str

    def __str__(self) -> str:
        return self.signature

    def name(self) -> str:
        """
        Extracts the function name from a mangled function signature

        Example:
            ms = MangledSignature("_ZN5fname_PN3_param1_param2_param3_QN0_R")
            ms.name()
            ->
            fname

        Returns:
            str: the function name in the function signature
        """
        name_remains = self.signature.split("_PN")[0]
        name_and_length = name_remains.split("_ZN")[1]
        length = 0
        while name_and_length[length].isdigit():
            length += 1
        return name_and_length[length:]

    def params(self) -> list[str]:
        """
        Extracts the parameters from a mangled function signature

        Example:
            ms = MangledSignature("_ZN5fname_PN3_param1_param2_param3_QN0_R")
            ms.params()
            ->
            ['param1', 'param2', 'param3']

        Returns:
            list[str]: the parameters in the function signature
        """
        name_removed = self.signature.split("_PN")[1]
        just_params = name_removed.split("_QN")[0]
        return just_params.split("_")[1:]

    def qubits(self) -> list[str]:
        """
        Extracts the qubits from a mangled function signature

        Example:
            ms = MangledSignature("_ZN5fname_PN0_QN3_$1_$3_q_R")
            ms.qubits()
            ->
            ['$1', '$3', 'q']

        Args:
            mangled_name (str): mangled function signature

        Returns:
            list[str]: the qubits in the function signature
        """
        name_removed = self.signature.split("_QN")[1]
        just_params = name_removed.split("_R")[0]
        return just_params.split("_")[1:]

    def return_type(self) -> str:
        """
        Extracts the return type from a mangled function signature

        Example:
            ms = MangledSignature("_ZN5fname_PN0_QN0_RANGLE")
            ms.return_type()
            ->
            'ANGLE'

        Args:
            mangled_name (str): mangled function signature

        Returns:
            str: the return type in the function signature
        """
        return self.signature.split("_R")[1]

    def match(self, params: list[str], qubits: list[str]) -> float:
        # todo consider changing matching numbers to be extreme
        """
        determines how well lists of parameters and qubits match
        the mangled function signature. parameters and qubits can either fully,
        partially or not match the mangled function signature. A full match increases
        the result returned by 1 while partial parameter matches are weighted by the
        number of parameters in the function signature and partial qubit matches are
        weighted by both the number of parameters and qubits in the function signature.
        This is done such that uniqe results are yielded for each combination of matches

        Definition for full and partial matches:

        full parameter match:
            The number of parameters in the call to the match method we expect to
            have a 1:1 relation to the parameters in the mangled signature
        full qubit match:
            The number of qubits in the call to the match method we expect to
            have a 1:1 relation to the qubits in the mangled signature
        partial parameter match:
            The number of parameters in the call to the match method we expect to
            have a partial relation to the parameters in the mangled signature,
            currently any number is treated as a partial match
            (no type checking is performed)
        partial qubit match:
            The number of qubits in the call to the match method we expect to
            have a partial relation to the qubits in the mangled signature,
            currently if a physical qubit is called for a signature defined with
            a wildcard qubit (no $) it is determined to be a partial match

        Args:
            params (list[str]):
                list of parameters and/or values at call time to match to
                the mangled function signature
            qubits (list[str]):
                list of qubits and/or values at call time to match to
                the mangle function signature


        Returns:
            float: represents how well the parameters and qubits match the mangled
            function signature
        """
        matches = 0
        f_params = self.params()
        LOGGER.debug("Parameters for symbol: %s -- %s", self.signature, f_params)
        for param, f_param in zip(params, f_params):
            LOGGER.debug("Matching parameter: %s to symbol: %s", param, self.signature)
            if is_number(f_param):
                if param == f_param:
                    matches += 1
                    LOGGER.debug("Matched to %s", f_param)
                else:
                    # if the function if defined for a specific value
                    # it should only be used for that value
                    matches -= 100
            elif is_number(param):
                matches += 1.0 / (len(params) + 1)

        f_qubits = self.qubits()
        LOGGER.debug("Qubits for symbol: %s -- %s", self.signature, f_qubits)

        for qubit, f_qubit in zip(qubits, f_qubits):
            LOGGER.debug("Matching qubit: %s to symbol: %s", qubit, self.signature)
            if qubit == f_qubit or ("$" not in qubit and "$" not in f_qubit):
                # perfect match between physical qubits or both arb.
                matches += 1
                LOGGER.debug("Matched to %s", f_qubit)
            elif "$" in qubit and "$" not in f_qubit:
                # function signature defined for arb qubit, called with physical qubit
                matches += 1 / ((len(params) + 1) * (len(qubits) + 1))
            elif "$" in f_qubit:
                # function signature defined for specific physical qubit
                matches -= 1000
        return matches


class FunctionSignature(BaseModel):
    """
    Pydantic model for openQASM function signatures (subrotines, extern, gates, defcals)
    Has methods for:
        mangling the FunctionSignature objects into a single string
        matching FunctionSignature objects to a mangled signature from a list
            of mangled signatures
    """

    name: str
    params: list[str] = Field(default_factory=lambda: [])
    qubits: list[str] = Field(default_factory=lambda: [])
    return_type: str = ""

    def mangle(self) -> str:
        """
        Mangles function names + call signature + return type in order to allow
        overloading functions with the same name.
        E.g., to allow defining the same gate for multiple different qubits, i.e.
            'defcal x $0' -> '_ZN1x_PN0_QN1_$0_R'
            'defcal x $1' -> '_ZN1x_PN0_QN1_$1_R'

        The mangled name will start with '_ZN' followed by the number of letters
        in the function name. Followed by the function name.

        Next we have '_PN' followed by the number of parameters in the function
        signature.
        Followed by '_' and the parameter for each parameter in the function signature

        Next we have '_QN' followed by the number of qubts in the function signature.
        Followed by '_' and the qubit for each qubit in the function signature

        Finally we have '_R' followed by the type of the variable returned by the
        function

        This name mangling scheme is based on the one for C++
        https://en.wikipedia.org/wiki/Name_mangling#C++

        Args:
            base_name (str):
                name of the function to mangle
            params (list[str], optional):
                parameters in the function signature. Defaults to None.
            qubits (list[str], optional):
                qubits in the function signature. Defaults to None.
            return_type (str, optional):
                type of the return variable of the function. Defaults to None.

        Returns:
            str: mangled function signature
        """
        LOGGER.debug("Mangling signature %s", self)
        mangled = (
            f"_ZN{len(self.name)}{self.name}"
            + f"_PN{len(self.params)}"
            + ("_" if len(self.params) > 0 else "")
            + "_".join(self.params)
            + f"_QN{len(self.qubits)}"
            + ("_" if len(self.qubits) > 0 else "")
            + "_".join(self.qubits)
            + f"_R{self.return_type}"
        )
        LOGGER.debug("Mangled signature %s", mangled)
        return mangled

    def match(self, mangled_names: list[str]) -> list[str]:
        """Matches the FunctionSignature to a mangled function signature from a
        list of mangled function signatures, used to match function calls to
        function definitions.

        Args:
            mangled_names (list[str]): list of mangled function signatures

        Returns:
            str: The mangled function signature that best matches the FunctionSignature
            object, if the function name, number of params and number of qubits don't
            match any of the mangled signatures None will be returned
        """

        def filter_symbols(symbols: list[str], term: str) -> list[str]:
            filtered_symbols = [symbol for symbol in symbols if term in symbol]
            LOGGER.debug("Filtering symbols for '%s'", term)
            LOGGER.debug("Filtered symbols: %s", filtered_symbols)
            return filtered_symbols

        LOGGER.debug("Function symbols: %s", mangled_names)
        f_symbols = filter_symbols(mangled_names, f"_ZN{len(self.name)}{self.name}")
        f_symbols = filter_symbols(f_symbols, f"_PN{len(self.params)}")
        f_symbols = filter_symbols(f_symbols, f"_QN{len(self.qubits)}")

        match_dict = {
            symbol: MangledSignature(signature=symbol).match(self.params, self.qubits)
            for symbol in f_symbols
        }

        LOGGER.debug("Matching dictionary: %s", match_dict)

        # filter out functions with incorrect physical qubit or literal match(es)
        match_dict = {k: v for k, v in match_dict.items() if v >= 0}

        best_matched_symbols = [
            symbol
            for symbol, matches in match_dict.items()
            if matches == max(match_dict.values())
        ]
        return best_matched_symbols


class Mangler(LiteralVisitor, TypeVisitor, GenericVisitor):
    """
    QASMVisitor that visits CalibrationDefinition or QuantumGate nodes to gather
    the iformation required to mangle function definition signatures and function calls
    """

    def __init__(
        self, node: ast.CalibrationDefinition | ast.QuantumGate = None
    ) -> None:
        super().__init__()
        self.name = None
        self.qubits = None
        self.arguments = None
        self.return_type = None
        if node:
            self.visit(node)

    def signature(self) -> FunctionSignature:
        """Converts instances of Mangler class to FunctionSignature objects

        Returns:
            FunctionSignature:
                with name, params qubits and return_type from the Mangler class instance
        """
        return FunctionSignature(
            name=self.name,
            params=self.arguments,
            qubits=self.qubits,
            return_type=self.return_type,
        )

    # pylint: disable=C0103
    # disable snake_case naming style
    # these functions are of the form "visit_{QASMNode class name}"
    def visit_CalibrationDefinition(self, node: ast.CalibrationDefinition):
        """
        CalibrationDefinition node visitor
            Extracts name, arguments, qubits and return_type from the node
            and makes them usable for mangling

        Args:
            node (ast.CalibrationDefinition):
                openQASM defcal statement to visit
        """
        self.name = self.visit(node.name)
        self.arguments = [self.visit(arg) for arg in node.arguments]
        self.qubits = [self.visit(qubit) for qubit in node.qubits]
        self.return_type = self.visit(node.return_type) if node.return_type else ""

    def visit_QuantumGate(self, node: ast.QuantumGate):
        """
        QuantumGate node visitor
            Extracts name, arguments, qubits and return_type from the node
            and makes them usable for mangling

        Args:
            node (ast.QuantumGate):
                openQASM quantum gate call node to visit
        """
        self.name = self.visit(node.name)
        self.arguments = [self.visit(arg) for arg in node.arguments]
        self.qubits = [self.visit(qubit) for qubit in node.qubits]
        self.return_type = ""

    def visit_QuantumReset(self, node: ast.QuantumReset):
        """
        QuantumReset node visitor
            Extracts qubits from the node.
            To be usable for mangling the following operations are performed
            name is set to "reset"
            arguments are set to empty ([])
            return_type is set to empty string ("")

        Args:
            node (ast.QuantumReset):
                openQASM quantum reset node to visit
        """
        match node:
            case ast.QuantumReset(ast.Identifier(q)):
                self.name = "reset"
                self.arguments = []
                self.qubits = [q]
                self.return_type = ""
            case ast.QuantumReset(ast.IndexedIdentifier()):
                raise NotImplementedError
            case _:
                raise NotImplementedError  # this should not happen on correct trees

    def visit_QuantumMeasurement(self, node: ast.QuantumMeasurement):
        """
        QuantumMeasurement node visitor
            Extracts qubits from the node.
            To be usable for mangling the following operations are performed
            name is set to "measure"
            arguments are set to empty ([])
            return_type is set "BIT"

        Args:
            node (ast.QuantumMeasurement):
                openQASM quantum measurement node to visit
        """
        match node:
            case ast.QuantumMeasurement(ast.Identifier(q)):
                self.name = "measure"
                self.arguments = []
                self.qubits = [q]
                self.return_type = "BIT"
            case ast.QuantumMeasurement(ast.IndexedIdentifier()):
                raise NotImplementedError
            case _:
                raise NotImplementedError  # this should not happen on correct trees

    def visit_Identifier(self, node: ast.Identifier) -> str:
        """
        Identifier node visitor

        Args:
            node (ast.Identifier):
                openQASM identifier node to visit

        Returns:
            str: the name of the identifier
        """
        return node.name

    def visit_ClassicalArgument(self, node: ast.ClassicalArgument) -> str:
        """
        ClassicalArgument node visitor

        Args:
            node (ast.ClassicalArgument):
                openQASM classical argument node to visit

        Returns:
            str: the type of the classical argument
        """
        return self.visit(node.type)

    # pylint: enable=C0103
