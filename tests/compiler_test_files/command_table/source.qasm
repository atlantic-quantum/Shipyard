OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
    extern executeTableEntry(int) -> waveform;
    port dac0;
    port dac1;
    port adc0;
    frame flux_bias = newframe(dac1, 0, 0);
    frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
    play(tx_frame_0, executeTableEntry(0));
}
defcal gate_1 $0 {
    delay[1200.0ns] tx_frame_0;
    play(flux_bias, executeTableEntry(2));
}
defcal gate_2 $1 {
    play(rx_frame_0, executeTableEntry(1));
}
gate_1 $0;
gate_2 $1;