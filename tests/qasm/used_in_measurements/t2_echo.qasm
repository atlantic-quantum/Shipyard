// echo
OPENQASM 3.0;
defcalgrammar "openpulse";
const complex ii = 1.0im;

input duration start_time;
input duration time_step;
input int n_steps;
input int n_shots;
input duration capture_time;
input float resonator_frequency;
input float qubit_frequency;
input float xhalf_drive_amp;
input duration xhalf_drive_time;
input float x_drive_amp;
input duration x_drive_time;
input duration wait_time;

const duration start_time_internal = start_time / 2;
const duration time_step_internal = time_step / 2;

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

defcal xhalf $0 {
    delay[xhalf_drive_time] tx_frame_0;
    play(spec_frame, ones(xhalf_drive_time) * xhalf_drive_amp);
}

defcal x $0 {
    delay[x_drive_time] tx_frame_0;
    play(spec_frame, ones(x_drive_time) * x_drive_amp);
}

defcal y $0 {
    delay[x_drive_time] tx_frame_0;
    play(spec_frame, ii * (ones(x_drive_time) * x_drive_amp));
}

defcal measure $0 {
    delay[capture_time] spec_frame;
    capture_v1_spectrum(rx_frame_0, capture_time);
}

defcal reset $0 {
    delay[wait_time] spec_frame;
    delay[wait_time] tx_frame_0;
}


cal {
    barrier;

    for int i in [0:n_steps] {
        for int j in [0:n_shots] {
            duration delay_time = (start_time_internal + i * time_step_internal);

            xhalf $0;

            delay[delay_time] spec_frame;
            delay[delay_time] rx_frame_0;

            y $0;
            
            delay[delay_time] spec_frame;
            delay[delay_time] rx_frame_0;

            xhalf $0;

            // for ZI glitch
            delay[24.0ns] spec_frame;
            delay[24.0ns] tx_frame_0;

            measure $0;
            reset $0;

        }
    }
}
