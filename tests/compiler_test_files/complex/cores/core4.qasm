OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern constant(duration, float[64]) -> waveform;
  extern gaussian(duration, duration, float[64]) -> waveform;
  port dac3;
  port adc0;
  frame tx_frame_0 = newframe(dac3, 5700000000.0, 0);
  frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
  frame tx_frame_1 = newframe(dac3, 5800000000.0, 0);
  frame rx_frame_1 = newframe(adc0, 5800000000.0, 0);
  frame tx_frame_2 = newframe(dac3, 5900000000.0, 0);
  frame rx_frame_2 = newframe(adc0, 5900000000.0, 0);
}
bit feedback_bit;
defcal reset $0 {
  delay[2000000dt] tx_frame_0;
}
defcal measure $0 -> bit {
  play(tx_frame_0, ones(4800dt) * 0.2);
  return capture_v2(rx_frame_0, ones(4800dt) * 1);
}
defcal x90 $0 {
  delay[64dt] tx_frame_0;
}
defcal x $0 {
  x90 $0;
  x90 $0;
}
defcal reset $1 {
  delay[2000000dt] tx_frame_1;
}
defcal measure $1 -> bit {
  play(tx_frame_1, ones(4800dt) * 0.2);
  return capture_v2(rx_frame_1, ones(4800dt) * 1);
}
defcal x90 $1 {
  delay[64dt] tx_frame_1;
}
defcal y90 $1 {
  x90 $1;
}
defcal reset $2 {
  delay[2000000dt] tx_frame_2;
}
defcal measure $2 -> bit {
  play(tx_frame_2, ones(4800dt) * 0.2);
  return capture_v2(rx_frame_2, ones(4800dt) * 1);
}
defcal x90 $2 {
  delay[64dt] tx_frame_2;
}
defcal Idle90 $2 {
  delay[64dt] tx_frame_2;
}
defcal x $2 {
  x90 $2;
  x90 $2;
}
defcal cnot $0, $1 {
  delay[2000000dt] tx_frame_0;
  delay[2000000dt] tx_frame_1;
}
defcal cphase $2, $0 {
  delay[2000000dt] tx_frame_0;
  delay[2000000dt] tx_frame_2;
}
defcal arb_pulse $0 {
  delay[32dt] tx_frame_0;
}
for int shot_index in [0:99] {
  reset $0;
  reset $1;
  reset $2;
  x $0;
  y90 $1;
  cnot $0, $1;
  feedback_bit = measure $1;
  if (feedback_bit) {
    x $2;
  } else {
    Idle90 $2;
    Idle90 $2;
  }
  arb_pulse $0;
  cphase $2, $0;
}