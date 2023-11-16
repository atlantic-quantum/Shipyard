from pathlib import Path

from shipyard.compiler import visualize_pulses


if __name__ == "__main__":
    setup_path = Path(__file__).parent.parent / "tests/setups/interpreter.json"
    qasm_path = Path(__file__).parent.parent / "tests/qasm/visualize_pulse/forloop.qasm"
    visualize_pulses(qasm_path, setup_path)
