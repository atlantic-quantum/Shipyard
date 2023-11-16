OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port dac1;
  frame xy_frame_1 = newframe(dac1, 6500000000.0, 0.0);
}
cal {
  extern constant(duration, float[64]) -> waveform;
  extern gaussian(duration, duration, float[64]) -> waveform;
}
bit feedback_bit;
defcal reset $1 {
  delay[2000000dt] xy_frame_1;
}
defcal measure $1 {
  delay[4800dt] xy_frame_1;
}
defcal x90 $1 {
  play(xy_frame_1, gauss(32, 1.0, 16, 8) * 0.2063);
}
defcal z90 $1 {
  shift_phase(xy_frame_1, 1.5707963267948966);
}
defcal y90 $1 {
  z90 $1;
  x90 $1;
}
defcal cnot $0, $1 {
  delay[2000000dt] xy_frame_1;
}
for int shot_index in [0:99] {
  reset $1;
  y90 $1;
  cnot $0, $1;
  measure $1;
  if (feedback_bit) {
  }
}