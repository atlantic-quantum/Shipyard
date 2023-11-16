OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port dac3;
  port adc0;
  frame tx_frame_0 = newframe(dac3, 5700000000.0, 0);
  frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}
defcal x $0 {
  delay[2400dt] tx_frame_0;
}
defcal measure $0 -> bit {
  play(tx_frame_0, ones(4800dt) * 0.3);
  return capture_v2(rx_frame_0, ones(4800dt) * 0.9);
}
bit measured_bit_0;
barrier;
x $0;
measured_bit_0 = measure $0;