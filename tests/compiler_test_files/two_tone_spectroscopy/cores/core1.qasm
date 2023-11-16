OPENQASM 3.0;
defcalgrammar "openpulse";
const int n_steps = 100;
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
  for int i in [0:n_steps] {
    delay[2528dt] tx_frame_0;
    measure_resonator $0;
  }
}