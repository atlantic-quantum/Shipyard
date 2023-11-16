OPENQASM 3.0;
defcalgrammar "openpulse";
const duration time_start = 2000dt;
const duration time_delta = 40000dt;
const int n_steps = 5;
const int n_shots = 2;
cal {
  port dac0;
  port adc0;
  frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);
  frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}
defcal xhalf $0 {
  delay[2400dt] tx_frame_0;
}
defcal delay_0(duration time) $0 {
  delay[time] tx_frame_0;
}
defcal measure $0 -> bit {
  play(tx_frame_0, ones(4800dt) * 0.3);
  return capture_v2(rx_frame_0, ones(4800dt) * 0.9);
}
defcal reset $0 {
  delay[2000dt] tx_frame_0;
}
barrier;
for int j in [0:n_shots] {
  for int i in [0:n_steps] {
    duration delay_time = time_start + i * time_delta;
    xhalf $0;
    delay_0(delay_time) $0;
    xhalf $0;
    measure $0;
    reset $0;
  }
}
