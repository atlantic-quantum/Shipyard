OPENQASM 3.0;

cal {
  port dac0;
  port adc0;
  frame rx_frame = newframe(adc0, 7e9, 0);
  frame tx_frame = newframe(dac0, 7e9, 0);
  let first_alias = sine(16, 1.0, 0, 0.25) ++ ones(160) ++ sine(16, 1.0, 3.14/2, 0.25);
  play(tx_frame, first_alias);
  let second_alias = sine(16, 1.0, 0, 0.25) ++ ones(160) ++ sine(16, 1.0, 3.14/2, 0.25);
  capture_v1(rx_frame, 0.55*second_alias);
}