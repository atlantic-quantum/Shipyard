// Testing functioncalls for setting and shifting phase and frequency of a frame
OPENQASM 3.0;

float f1 = 3000.0;
float f2 = 4000.0;
float p1 = 1.0;


cal {
    port dac1;
    port dac0;
    frame spec_frame = newframe(dac1, 4000000000.0, 0);
    frame tx_frame_0 = newframe(dac0, 7000000000.0, 0);
    set_frequency(tx_frame_0, f1);
    set_frequency(spec_frame, f2);
    set_phase(spec_frame, 2.0);
    set_phase(tx_frame_0, p1);
}

cal {
    shift_frequency(spec_frame, 1000.0);
    shift_phase(tx_frame_0, 0.5);
}