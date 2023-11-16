OPENQASM 3.0;
defcalgrammar "openpulse";
delay[10.0ns] $0;
cal {
  port awg1_ch1;
  frame frame1 = newframe(awg1_ch1, 0, 0);
  waveform w_gauss_1 = 1.0 * gauss(8000.0dt, 1.0, 4000.0dt, 1000.0dt);
  play(frame1, w_gauss_1);
}
defcal my_gate $1 {
  play(frame1, w_gauss_1);
}
my_gate $1;