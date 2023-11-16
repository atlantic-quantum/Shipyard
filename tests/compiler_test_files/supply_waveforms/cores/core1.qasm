OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  waveform supplied_waveform1 = placeholder(112dt);
}
cal {
  port awg1_ch1;
  frame frame1 = newframe(awg1_ch1, 0, 0);
  play(frame1, supplied_waveform1);
}