OPENQASM 3.0;
defcalgrammar "openpulse";
// this example performs resonator spectroscopy and raw waveforms at each frequency

const float frequency_start = -750e6;
const float frequency_step = 15e6;
const int n_steps = 100;
const duration capture_time = 1008.0ns;

cal {
    port dac1;
    port adc0;
    frame tx_frame_0 = newframe(dac1, 5700000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
    for int i in [0:n_steps] {
        delay[200.0ns] tx_frame_0;
        set_frequency(tx_frame_0, frequency_start+i*frequency_step);
        capture_v3(rx_frame_0, capture_time);
    }
}