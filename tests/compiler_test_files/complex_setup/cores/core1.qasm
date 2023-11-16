OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port dac0;
  frame xy_frame_0 = newframe(dac0, 6400000000.0, 0.0);
}
cal {
  extern constant(duration, float[64]) -> waveform;
  extern gaussian(duration, duration, float[64]) -> waveform;
  waveform wfm_arb = {-1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75, -1.0, 0.5, 0.25, -0.75};
}
bit feedback_bit;
defcal reset $0 {
  delay[2000000dt] xy_frame_0;
}
defcal measure $0 {
  delay[4800dt] xy_frame_0;
}
defcal x90 $0 {
  play(xy_frame_0, gauss(32, 1.0, 16, 8) * 0.2063);
}
defcal z90 $0 {
  shift_phase(xy_frame_0, 1.5707963267948966);
}
defcal rz(angle[32] theta) $0 {
  shift_phase(xy_frame_0, theta);
}
defcal rz(1) $0 {
  shift_phase(xy_frame_0, 1);
}
defcal x $0 {
  x90 $0;
  x90 $0;
}
defcal cnot $0, $1 {
  delay[2000000dt] xy_frame_0;
}
defcal cphase $2, $0 {
  delay[2000000dt] xy_frame_0;
}
defcal arb_pulse $0 {
  play(xy_frame_0, wfm_arb);
}
for int shot_index in [0:99] {
  reset $0;
  x $0;
  rz(1) $0;
  rz(1.5707963267948966) $0;
  cnot $0, $1;
  if (feedback_bit) {
  }
  arb_pulse $0;
  cphase $2, $0;
}