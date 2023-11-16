
OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
  extern placeholder(int) -> waveform;
  waveform my_wave = placeholder(50);
  port ch1;
  frame lab_frame = newframe(ch1, 0, 0);
  play(lab_frame, my_wave);
}