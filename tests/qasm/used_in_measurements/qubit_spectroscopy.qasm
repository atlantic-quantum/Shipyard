OPENQASM 3.0;
defcalgrammar "openpulse";

input float frequency_start;
input float frequency_step;
input int n_steps;
input int n_shots;
input duration capture_time;
input float resonator_frequency;
input duration drive_time;
input float drive_amplitude;


cal {
    port dac2;
    frame spec_frame = newframe(dac2, 4000000000.0, 0);

    port dac0;
    frame tx_frame_0 = newframe(dac0, 7000000000.0, 0);
    delay[200.0ns] tx_frame_0;
    set_frequency(tx_frame_0, resonator_frequency);

    port adc0;
    frame rx_frame_0 = newframe(adc0, 7000000000.0, 0);
}



cal {
    barrier;

    // measurement loop
    for int i in [0:n_steps] {

        // set drive frequency
        delay[200.0ns] spec_frame;
        delay[200.0ns] tx_frame_0;
        set_frequency(spec_frame, frequency_start+i*frequency_step);

        for int j in [0:n_shots] {
            
            // play drive tone
            play(spec_frame, ones(drive_time)*drive_amplitude);
            delay[drive_time] tx_frame_0;

            // for ZI glitch
            delay[24.0ns] spec_frame;
            delay[24.0ns] tx_frame_0;

            // measure resonator
            delay[capture_time] spec_frame;
            capture_v1_spectrum(rx_frame_0, capture_time);

            delay[2.0us] tx_frame_0;
            delay[2.0us] spec_frame;
        }
    }
}