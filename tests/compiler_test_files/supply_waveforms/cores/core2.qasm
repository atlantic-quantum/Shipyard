OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  waveform supplied_waveform2 = placeholder(112dt);
}
cal {
  port awg2_ch1;
  frame frame2 = newframe(awg2_ch1, 0, 0);
  play(frame2, supplied_waveform2);
}