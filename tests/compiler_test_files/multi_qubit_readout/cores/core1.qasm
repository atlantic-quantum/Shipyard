OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port dac1;
  frame flux_bias = newframe(dac1, 0, 0);
  frame xy_frame_1 = newframe(dac1, 6500000000.0, 0);
}
defcal measure $0 {
  delay[32dt] flux_bias;
}
defcal measure $1 {
  delay[64dt] xy_frame_1;
}
def measure_func(qubit[num_qubits] q, int num_qubits) -> bit[1] {
  bit[num_qubits] r;
  measure $0;
  measure $1;
  return r;
}
int num_qubits = 2;
bit[num_qubits] b;
qubit[num_qubits] q;
b = measure_func(q, num_qubits);