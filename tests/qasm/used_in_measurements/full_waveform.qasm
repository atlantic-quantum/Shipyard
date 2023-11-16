OPENQASM 3.0;
defcalgrammar "openpulse";

input int n_shots;
input float resonator_frequency;
input duration capture_time;
input float waveform_idle_value;
input duration waveform_duration;
input duration readout_delay;
input duration wait_time;


cal {
    port dac3;
    port dac0;
    port adc0;
    frame bias_frame = newframe(dac3, 0, 0);
    frame tx_frame = newframe(dac0, 0, 0);
    frame rx_frame = newframe(adc0, 0, 0);
    set_frequency(tx_frame, resonator_frequency);

    barrier;
    for int i in [0:n_shots] {

        // play waveform
        play(bias_frame, waveform1);
        delay[waveform_duration] tx_frame; // future update will enable this line to be "delay[durationof(waveform)] tx_frame;"

        // for ZI glitch
        play(bias_frame, waveform_idle_value * ones(24.0ns));
        delay[24.0ns] tx_frame;

        // readout delay
        delay[readout_delay] bias_frame;
        delay[readout_delay] tx_frame;

        // readout
        capture_v1_spectrum(rx_frame, capture_time);
        play(bias_frame, waveform_idle_value * ones(capture_time));

        // wait after readout
        delay[wait_time] bias_frame;
        delay[wait_time] tx_frame;
    }
}