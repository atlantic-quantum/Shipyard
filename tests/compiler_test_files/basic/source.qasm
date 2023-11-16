OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
  port awg1_ch1;
  port awg2_ch1;
  frame frame1 = newframe(awg1_ch1, 0, 0);
  frame frame2 = newframe(awg2_ch1, 0, 0);
  waveform w_gauss_1 = 1.0*gauss(8000dt, 1.0, 4000dt, 1000dt);
  waveform w_gauss_2 = 1.0*gauss(8000dt, 1.0, 4000dt, 2000dt);
  play(frame1, w_gauss_1);
  play(frame2, w_gauss_2);
}

defcal my_gate $1 {
  play(frame1, w_gauss_1);
}

defcal my_gate $2 {
  play(frame2, w_gauss_2);
}

my_gate $1;
my_gate $2;