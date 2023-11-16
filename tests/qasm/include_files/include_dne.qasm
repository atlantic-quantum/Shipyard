OPENQASM 3.0;
defcalgrammar "openpulse";
// this example performs ramsey measurement


const duration time_start = 0s;
const duration time_delta = 20us;
const int n_steps = 5;
include "file_does_not_exist.inc";

const int n_shots = 2;


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

barrier;

for int j in [0:n_shots] {
    for int i in [0:n_steps] {
        duration delay_time = time_start + i * time_delta;
        xhalf $0;
        delay_0(delay_time) $0;
        xhalf $0;
        measure $0;
        reset $0;
    }
}