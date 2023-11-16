OPENQASM 3.0;
defcalgrammar "openpulse";
// this example performs pulsed two tone spectroscopy and returns complex value at each frequency
// plays a 1 us variable tone using SHFSG followed by 1 us fixed tone + caputre using SHFQA

const float frequency_start = -750e6;
const float frequency_step = 15e6;
const int n_steps = 100;

cal {
    port dac0;
    port dac1;
    port adc0;
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
    for int i in [0:n_steps] {
        delay[256.0ns] spec_frame;  // it is important this delay is before the set_frequency
        set_frequency(spec_frame, frequency_start+i*frequency_step);
        play(spec_frame, ones(1008.ns));
        delay[1264.0ns] tx_frame_0;
        measure_resonator $0;
    }
}