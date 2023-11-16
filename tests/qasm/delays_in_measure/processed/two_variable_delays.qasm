OPENQASM 3.0;
defcalgrammar "openpulse";


cal {
    port dac0;
    port dac3;
    port dac1;
    port adc0;
    duration delay_1 = 4ns;
    duration delay_2 = 2ns;
    frame flux_bias = newframe(dac1, 0, 0);
    frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
    frame tx_frame_1 = newframe(dac3, 5800000000.0, 0);
    frame rx_frame_1 = newframe(adc0, 5800000000.0, 0);
    frame xy_frame_1 = newframe(dac1, 6500000000.0, 0);
}

defcal measure $0 -> bit {
    delay[4ns] flux_bias;
    play(tx_frame_0, ones(3ns)*0.3);
    return capture_v2(rx_frame_0, ones(3ns)*0.9);
}

defcal measure $1 -> bit {
    delay[4ns] xy_frame_1;
    play(tx_frame_1, ones(5ns)*0.2);
    return capture_v2(rx_frame_1, ones(5ns)*1);
}

def measure_func(qubit[num_qubits] q, int num_qubits) -> bit[1] {
    bit[num_qubits] r;
    r[0] = measure $0;
    r[1] = measure $1;
    return r;
}

int num_qubits = 2;
bit[num_qubits] b;
qubit[num_qubits] q;
//measure $1;
b = measure_func(q, num_qubits);