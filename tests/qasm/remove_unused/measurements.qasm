OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port ch1;
  frame tx_frame = newframe(ch1, 0, 0);
  frame rx_frame = newframe(ch1, 0, 0);
  waveform w_gauss = 1.0*gauss(8000dt, 1.0, 4000dt, 1000dt);
}
defcal measure $0 -> bit {
  play(tx_frame, w_gauss);
  return capture_v2(rx_frame, w_gauss)
}
bit measured_bit_0;
bit measured_bit_1;
measured_bit_0 = measure $0;
measured_bit_1 = measure $1;