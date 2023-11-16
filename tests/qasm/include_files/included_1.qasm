OPENQASM 3.0;
defcalgrammar "openpulse";
//first nested include in ramsey experiment
include "included_2.inc";

cal {
    port dac0;
    port dac1;
    port adc0;
    frame flux_bias = newframe(dac1, 0, 0);
    frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}

defcal xhalf $0 {
    delay[1200.0ns] tx_frame_0;
    play(flux_bias, ones(1200.0ns)*0.2);
}

defcal delay_0(duration time) $0 {
    delay[time] flux_bias;
    delay[time] tx_frame_0;
}

defcal measure $0 -> bit {
    delay[2400.0ns] flux_bias;
    play(tx_frame_0, ones(2400.0ns)*0.3);
    return capture_v2(rx_frame_0, ones(2400.0ns)*0.9);
}

defcal reset $0 { // kept short for demonstration purposes
    delay[1000.0ns] flux_bias;
    delay[1000.0ns] tx_frame_0;
}