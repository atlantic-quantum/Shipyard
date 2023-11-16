# Atlantic Quantum Compiler

Compiler developed by Atlantic Quantum to compile openQASM + openPulse code to vendor specific instructions. Currently supports compilation to Zurich Instruments SEQC, more instrument vendors will be supported in the future.

## Status

AQ Compiler is in daily use by Atlantic Quantum to perform quantum experiments.

## Usage

The compiler will take information from three sources and compile them to instrument instructions.

1. A QASM file to be executed, can contain `openPulse` definitions of gate operations
2. A Configuration file that maps 'Frames' and 'Ports' to specific instrument channels.
3. An optional dictionary, of input name value pairs, used to populate any 'input' variables in the qasm file during compilation

### Usage Example

```python
from shipyard import Compiler

qasm_file = "path/to/some/qasm/file.qasm"
setup_file = "path/to/some/setup/file.yml" # or json file

# create a compiler instance with qasm and setup files
compiler = Compiler(qasm_file, setup_file)

# compile the qasm program with optional 'input' values
input_dict = {"input1": 1e-7, "input2": 0.34} # optional
compiler.compile(input_dict)

# access combined full qasm program
compiler.program: openqasm3.ast.Program

# access per FPGA core qasm program
compiler.split_program: dict[core, openqasm3.ast.Program]

# access per FPGA core instrument specific instructions
compiler.split_compiled: dict[core, str]
```