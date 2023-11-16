OPENQASM 3.0;
defcalgrammar "openpulse";
const duration time_start = 2000dt;
const duration time_delta = 40000dt;
const int n_steps = 5;
const int n_shots = 2;
cal {
  port dac1;
  frame flux_bias = newframe(dac1, 0, 0);
}
defcal xhalf $0 {
  play(flux_bias, ones(2400dt) * 0.2);
}
defcal delay_0(duration time) $0 {
  delay[time] flux_bias;
}
defcal measure $0 {
  delay[4800dt] flux_bias;
}
defcal reset $0 {
  delay[2000dt] flux_bias;
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