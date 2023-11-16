OPENQASM 3.0;
defcalgrammar "openpulse";
const complex ii = 1.0im;

cal {
    waveform wave_imag = drag(620, 1.0, 320, 10);

    port sg_ch1;
    frame frame2 = newframe(sg_ch1, 0, 0);

    play(frame2, wave_imag*ii);
}