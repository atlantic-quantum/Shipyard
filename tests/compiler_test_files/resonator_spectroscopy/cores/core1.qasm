OPENQASM 3.0;
defcalgrammar "openpulse";
const float frequency_start = -750000000.0;
const float frequency_step = 15000000.0;
const int n_steps = 100;
const duration capture_time = 2016dt;
cal {
  port dac1;
  port adc0;
  frame tx_frame_0 = newframe(dac1, 5700000000.0, 0);
  frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
  for int i in [0:n_steps] {
    delay[400dt] tx_frame_0;
    set_frequency(tx_frame_0, frequency_start + i * frequency_step);
    capture_v1_spectrum(rx_frame_0, capture_time);
  }
}