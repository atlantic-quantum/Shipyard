OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
    extern constant(duration, float[64]) -> waveform;
    extern gaussian(duration, duration, float[64]) -> waveform;
    waveform wfm_arb = {-1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75};
}
bit feedback_bit;
//stretch s;
defcal reset $0 {
    delay[1000000.0ns] xy_frame_0;
    delay[1000000.0ns] tx_frame_0;
}
defcal measure $0 -> bit {
    delay[2400.0ns] xy_frame_0;
    play(tx_frame_0, ones(2400.0ns)*0.2);
    return capture_v2(rx_frame_0, ones(2400.0ns)*1);
}
defcal x90 $0 {
    play(xy_frame_0, gauss(32, 1.0, 16, 8)*0.2063);
    delay[32.0ns] tx_frame_0;
}
defcal z90 $0 {
    shift_phase(xy_frame_0, 1.5707963267948966);
}
defcal y90 $0 {
    z90 $0;
    x90 $0;
}
defcal rz(angle[32] theta) $0 {
    shift_phase(xy_frame_0, theta);
}
defcal rz(1) $0 {
    shift_phase(xy_frame_0, 1);
}
defcal Idle90 $0 {
    delay[32.0ns] xy_frame_0;
    delay[32.0ns] tx_frame_0;
}
defcal x $0 {
    x90 $0;
    x90 $0;
}
defcal y $0 {
    y90 $0;
    y90 $0;
}
defcal z $0 {
    z90 $0;
    z90 $0;
}
defcal reset $1 {
    delay[1000000.0ns] xy_frame_1;
    delay[1000000.0ns] tx_frame_1;
}
defcal measure $1 -> bit {
    delay[2400.0ns] xy_frame_1;
    play(tx_frame_1, ones(2400.0ns)*0.2);
    return capture_v2(rx_frame_1, ones(2400.0ns)*1);
}
defcal x90 $1 {
    play(xy_frame_1, gauss(32, 1.0, 16, 8)*0.2063);
    delay[32.0ns] tx_frame_1;
}
defcal z90 $1 {
    shift_phase(xy_frame_1, 1.5707963267948966);
}
defcal y90 $1 {
    z90 $1;
    x90 $1;
}
defcal rz(angle[32] theta) $1 {
    shift_phase(xy_frame_1, theta);
}
defcal rz(1) $1 {
    shift_phase(xy_frame_1, 1);
}
defcal Idle90 $1 {
    delay[32.0ns] xy_frame_1;
    delay[32.0ns] tx_frame_1;
}
defcal x $1 {
    x90 $1;
    x90 $1;
}
defcal y $1 {
    y90 $1;
    y90 $1;
}
defcal z $1 {
    z90 $1;
    z90 $1;
}
defcal reset $2 {
    delay[1000000.0ns] xy_frame_2;
    delay[1000000.0ns] tx_frame_2;
}
defcal measure $2 -> bit {
    delay[2400.0ns] xy_frame_2;
    play(tx_frame_2, ones(2400.0ns)*0.2);
    return capture_v2(rx_frame_2, ones(2400.0ns)*1);
}
defcal x90 $2 {
    play(xy_frame_2, gauss(32, 1.0, 16, 8)*0.2063);
    delay[32.0ns] tx_frame_2;
}
defcal z90 $2 {
    shift_phase(xy_frame_2, 1.5707963267948966);
}
defcal y90 $2 {
    z90 $2;
    x90 $2;
}
defcal rz(angle[32] theta) $2 {
    shift_phase(xy_frame_2, theta);
}
defcal rz(1) $2 {
    shift_phase(xy_frame_2, 1);
}
defcal Idle90 $2 {
    delay[32.0ns] xy_frame_2;
    delay[32.0ns] tx_frame_2;
}
defcal x $2 {
    x90 $2;
    x90 $2;
}
defcal y $2 {
    y90 $2;
    y90 $2;
}
defcal z $2 {
    z90 $2;
    z90 $2;
}
defcal cnot $0, $1 {
    delay[1000000.0ns] xy_frame_0;
    delay[1000000.0ns] xy_frame_1;
    delay[1000000.0ns] tx_frame_0;
    delay[1000000.0ns] tx_frame_1;
}
defcal cphase $2, $0 {
    delay[1000000.0ns] xy_frame_0;
    delay[1000000.0ns] xy_frame_2;
    delay[1000000.0ns] tx_frame_0;
    delay[1000000.0ns] tx_frame_2;}
defcal arb_pulse $0 {
    play(xy_frame_0, wfm_arb);
    delay[16.0ns] tx_frame_0;
}
for int shot_index in [0:99] {
    reset $0;
    reset $1;
    reset $2;
    x $0;
    y90 $1;
    rz(1) $0;
    rz(1.5707963267948966) $0;
    cnot $0, $1;
    feedback_bit = measure $1;
    if (feedback_bit) {
        x $2;
    } else {
        Idle90 $2;
        Idle90 $2;
    }
    //delay[s] $0;
    arb_pulse $0;
    cphase $2, $0;
}