OPENQASM 3.0;
defcalgrammar "openpulse";
delay[10.0ns] $0;
cal {
  port awg2_ch1;
  frame frame2 = newframe(awg2_ch1, 0, 0);
  waveform w_gauss_2 = 1.0 * gauss(8000.0dt, 1.0, 4000.0dt, 2000.0dt);
  play(frame2, w_gauss_2);
}
defcal my_gate $2 {
  play(frame2, w_gauss_2);
}
my_gate $2;