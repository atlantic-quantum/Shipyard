OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
    port dac0;
    port dac3;
    port adc0;
    frame frame_0 = newframe(dac0, 0, 0);
    frame tx_frame_0 = newframe(dac3, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}

defcal x $0 {
    delay[1200.0ns] tx_frame_0;
    play(frame_0, ones(1200.0ns)*0.2);
}

defcal measure $0 -> bit {
    delay[2400.0ns] frame_0;
    play(tx_frame_0, ones(2400.0ns)*0.3);
    return capture_v2(rx_frame_0, ones(2400.0ns)*0.9);
}

bit measured_bit_0;

barrier;
x $0;
measured_bit_0 = measure $0;