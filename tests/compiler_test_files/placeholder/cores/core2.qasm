OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern placeholder(int) -> waveform;
  port awg2_ch1;
  frame frame2 = newframe(awg2_ch1, 0, 0);
  waveform w_gauss_2 = placeholder(8000);
  play(frame2, w_gauss_2);
}
defcal my_gate $2 {
  play(frame2, w_gauss_2);
}
my_gate $2;