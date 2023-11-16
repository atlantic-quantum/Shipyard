OPENQASM 3.0;
defcalgrammar "openpulse";
// this example performs pulsed two tone spectroscopy and returns complex value at each frequency
// plays a 1 us variable tone using SHFSG followed by 1 us fixed tone + caputre using SHFQA

const float frequency_start = -750e6;
const float frequency_step = 30e6;
const int n_steps_freq = 40;

const float bias_start = -1.0;
const float bias_step = 0.04;
const int n_steps_flux = 50;

cal {
    port dac0;
    port dac1;
    port dac2;
    port adc0;
    frame flux_bias = newframe(dac2, 0, 0);
    frame spec_frame = newframe(dac0, 5000000000.0, 0);
    frame tx_frame_0 = newframe(dac1, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}

defcal measure_resonator $0 {
    delay[1008.0ns] spec_frame;
    play(tx_frame_0, ones(1008.0ns));
    capture_v1(rx_frame_0, ones(1008.0ns));
}

barrier;

cal {
    for int j in [0:n_steps_flux] {
        for int i in [0:n_steps_freq] {
            play(flux_bias, (bias_start + j * bias_step) * ones(2224.0ns));
            delay[208.0ns] spec_frame;
            set_frequency(spec_frame, frequency_start + i * frequency_step);
            play(spec_frame, ones(1008.0ns));
            delay[1216.0ns] tx_frame_0;
            measure_resonator $0;
        }
    }
}