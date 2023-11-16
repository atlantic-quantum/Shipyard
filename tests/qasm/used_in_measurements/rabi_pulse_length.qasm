// rabi pulse length experiment
OPENQASM 3.0;
defcalgrammar "openpulse";

input duration start_time;
input duration time_step;
input int n_steps;
input int n_shots;
input duration capture_time;
input float resonator_frequency;
input float qubit_frequency;
input float drive_amplitude;
input duration wait_time;


cal {
    port dac2;
    port dac0;
    port adc0;
    frame spec_frame = newframe(dac2, 4000000000.0, 0);
    frame tx_frame_0 = newframe(dac0, 7000000000.0, 0);
    frame rx_frame_0 = newframe(adc0, 7000000000.0, 0);
    delay[200.0ns] tx_frame_0;
    delay[200.0ns] spec_frame;
    set_frequency(tx_frame_0, resonator_frequency);
    set_frequency(spec_frame, qubit_frequency);
}

cal {
    barrier;

    for int i in [0:n_steps] {
        for int j in [0:n_shots] {

            // is there some delay missing here?
            play(spec_frame, ones(start_time + i * time_step) * drive_amplitude);
            delay[start_time + i * time_step] tx_frame_0;

            // for ZI glitch
            delay[24.0ns] spec_frame;
            delay[24.0ns] tx_frame_0;

            // readout
            delay[capture_time] spec_frame;
            capture_v1_spectrum(rx_frame_0, capture_time);

            // post readout wait
            delay[wait_time] spec_frame;
            delay[wait_time] tx_frame_0;
        }
    }
}
