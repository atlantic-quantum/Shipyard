import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from openpulse import ast, parse

from ..compiler_error import ErrorCode, TransformError
from ..utilities import ScopeContext
from ..visitors import CopyTransformer, GenericTransformer


class IncludeAnalyzer(GenericTransformer):
    """
    QASMTransformer loads in files that are included in the qasm program

    """

    def __init__(self, curr_path: Path) -> None:
        self.curr_path = curr_path
        self.context: ScopeContext = None

    # pylint: disable=C0103
    # snake_case naming

    def visit_Program(self, node: ast.Program):
        """
        Program (defcal) node transformer:
            Enters GLOBAL context and visits the program node
            Exits GLOBAL context before returning the node

        Args:
            node (ast.Program): openQASM program to process

        Returns:
            ast.Program: same node
        """
        with self.scope_manager(ScopeContext.GLOBAL):
            node.statements = self._visit_list_flatten(node.statements, self.visit)
        return node

    @staticmethod
    @lru_cache()
    def load_program(path: Path) -> ast.Program:
        """
        Loads a qasm program as an AST from a file

        Args:
            path (Path): path to the qasm program file

        Returns:
            ast.Program: qasm program as an AST
        """
        with open(path, encoding="utf_8") as qasm_file:
            qasm_code = qasm_file.read()
        return parse(qasm_code)

    def visit_Include(self, node: ast.Include):
        if os.path.isabs(node.filename):
            include_path = Path(node.filename)
        else:
            include_path = self.curr_path.parent / node.filename
        if not include_path.exists():
            raise TransformError(
                ErrorCode.INCLUDE_ERROR,
                f"Include file {include_path} does not exist, {node}",
            )
        program = CopyTransformer().visit_Program(self.load_program(include_path))
        # includes = [v for v in program.statements if isinstance(v, ast.Include)]
        include_indices = [
            i for i, s in enumerate(program.statements) if isinstance(s, ast.Include)
        ]
        if include_indices != []:
            with self.scope_manager(ScopeContext.GLOBAL):
                for i in include_indices:
                    new_statments = self.visit(program.statements[i])
                    program.statements[i : i + 1] = new_statments
                    # program.statements.extend(new_statments)
        return program.statements

    @contextmanager
    def scope_manager(self, context: ScopeContext):
        """
        Context manager for the scope of the qasm program.
        on entering the manager sets the context to the input context.
        restores the previous context on exiting the manager

        Args:
            context (ScopeContext): context to set while within the manager.
        """
        old_context = self.context
        try:
            self.context = context
            yield
        finally:
            self.context = old_context
