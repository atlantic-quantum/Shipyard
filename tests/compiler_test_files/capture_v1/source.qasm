// capture_v1 test
OPENQASM 3.0;
defcalgrammar "openpulse";

const duration capture_time = 2e-6s;

cal {
    port dac0;
    port adc0;
    frame tx_frame_0 = newframe(dac0, 7000000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 7000000000.0, 0);
}

defcal measure_v1 $0 {
    play(tx_frame_0, ones(capture_time));
    capture_v1(rx_frame_0, ones(capture_time));
}

cal {barrier;}

measure_v1 $0;
