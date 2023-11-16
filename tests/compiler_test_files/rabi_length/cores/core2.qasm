OPENQASM 3.0;
defcalgrammar "openpulse";
const duration start_time = 32.0dt;
const duration time_step = 32.0dt;
const int n_steps = 63;
const int n_shots = 2000;
const duration capture_time = 12000.0dt;
const float resonator_frequency = -300000000.0;
const duration wait_time = 4000.0dt;
cal {
  port dac0;
  port adc0;
  frame tx_frame_0 = newframe(dac0, 7000000000.0, 0);
  frame rx_frame_0 = newframe(adc0, 7000000000.0, 0);
  delay[400dt] tx_frame_0;
  set_frequency(tx_frame_0, resonator_frequency);
}
cal {
  barrier;
  for int i in [0:n_steps] {
    for int j in [0:n_shots] {
      delay[start_time + i * time_step] tx_frame_0;
      delay[48dt] tx_frame_0;
      capture_v1_spectrum(rx_frame_0, capture_time);
      delay[wait_time] tx_frame_0;
    }
  }
}