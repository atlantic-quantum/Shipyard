OPENQASM 3.0;
defcalgrammar "openpulse";
const int n_steps_freq = 40;
const int n_steps_flux = 50;
cal {
  port dac1;
  port adc0;
  frame tx_frame_0 = newframe(dac1, 5700000000.0, 0);
  frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}
defcal measure_resonator $0 {
  play(tx_frame_0, ones(2016dt));
  capture_v1(rx_frame_0, ones(2016dt));
}
barrier;
cal {
  for int j in [0:n_steps_flux] {
    for int i in [0:n_steps_freq] {
      delay[2432dt] tx_frame_0;
      measure_resonator $0;
    }
  }
}