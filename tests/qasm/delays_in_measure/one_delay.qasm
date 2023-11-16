OPENQASM 3.0;
defcalgrammar "openpulse";


cal {
    port dac0;
    port dac1;
    port adc0;
    frame flux_bias = newframe(dac1, 0, 0);
    frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}

defcal measure $0 -> bit {
    delay[3ns] flux_bias;
    play(tx_frame_0, ones(3ns)*0.3);
    return capture_v2(rx_frame_0, ones(3ns)*0.9);
}

def measure_func(qubit[num_qubits] q, int num_qubits) -> bit[1] {
    bit[num_qubits] r;
    r[0] = measure $0;
    return r;
}

int num_qubits = 1;
bit[num_qubits] b;
qubit[num_qubits] q;
//measure $1;
b = measure_func(q, num_qubits);
