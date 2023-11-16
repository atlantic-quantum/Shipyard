OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern executeTableEntry(int) -> waveform;
  port adc0;
  frame rx_frame_0 = newframe(adc0, 5700000000.0, 0);
}
defcal gate_2 $1 {
  play(rx_frame_0, executeTableEntry(1));
}
gate_2 $1;
