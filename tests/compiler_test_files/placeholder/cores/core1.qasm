OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern placeholder(int) -> waveform;
  port awg1_ch1;
  frame frame1 = newframe(awg1_ch1, 0, 0);
  waveform w_gauss_1 = placeholder(8000);
  play(frame1, w_gauss_1);
}
defcal my_gate $1 {
  play(frame1, w_gauss_1);
}
my_gate $1;