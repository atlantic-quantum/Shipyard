OPENQASM 3.0;
defcalgrammar "openpulse";
// this example performs resonator spectroscopy and raw waveforms at each frequency

input float frequency_start;
input float frequency_step;
input int n_steps;
input int n_shots;
input duration capture_time;

cal {
    port dac0;
    frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);

    port adc0;
    frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}

cal {
    barrier;

    // measurement loop
    for int i in [0:n_steps] {
        for int j in [0:n_shots] {

            // set resonator frequency
            set_frequency(tx_frame_0, frequency_start + i*frequency_step);
            
            // for ZI glitch (unsure if needed) 
            delay[24.0ns] tx_frame_0;

            // measure resonator            
            capture_v1_spectrum(rx_frame_0, capture_time);

            // delay between measurements
            delay[2.0us] tx_frame_0;
        }
    }

}