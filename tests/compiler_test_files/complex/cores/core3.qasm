OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern constant(duration, float[64]) -> waveform;
  extern gaussian(duration, duration, float[64]) -> waveform;
  port dac2;
  frame xy_frame_2 = newframe(dac2, 6600000000.0, 0);
}
bit feedback_bit;
defcal reset $2 {
  delay[2000000dt] xy_frame_2;
}
defcal measure $2 {
  delay[4800dt] xy_frame_2;
}
defcal x90 $2 {
  play(xy_frame_2, gauss(32, 1.0, 16, 8) * 0.2063);
}
defcal z90 $2 {
  shift_phase(xy_frame_2, 1.5707963267948966);
}
defcal Idle90 $2 {
  delay[64dt] xy_frame_2;
}
defcal x $2 {
  x90 $2;
  x90 $2;
}
defcal cphase $2, $0 {
  delay[2000000dt] xy_frame_2;
}
for int shot_index in [0:99] {
  reset $2;
  if (feedback_bit) {
    x $2;
  } else {
    Idle90 $2;
    Idle90 $2;
  }
  cphase $2, $0;
}