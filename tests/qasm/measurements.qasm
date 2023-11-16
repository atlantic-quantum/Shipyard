OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
    port dac3;
    port adc0;
    frame tx_frame_0 = newframe(dac3, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
    frame tx_frame_1 = newframe(dac3, 5800000000.0, 0);
    frame rx_frame_1 = newframe(adc0, 5800000000.0, 0);
}

defcal measure $0 -> bit {
    play(tx_frame_0, ones(2400.0ns)*0.2);
    return capture_v2(rx_frame_0, ones(2400.0ns)*1);
}

defcal measure $1 -> bit {
    play(tx_frame_1, ones(2400.0ns)*0.3);
    return capture_v2(rx_frame_1, ones(2400.0ns)*0.9);
}

bit measured_bit_0;
bit measured_bit_1;

measured_bit_0 = measure $0;
measured_bit_1 = measure $1;