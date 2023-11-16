OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
  port awg1_ch1;
  port awg2_ch1;
  frame frame1 = newframe(awg1_ch1, 0, 0);
  frame frame2 = newframe(awg2_ch1, 0, 0);
  play(frame1, supplied_waveform1);
  play(frame2, supplied_waveform2);
}