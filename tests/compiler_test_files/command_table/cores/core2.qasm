OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern executeTableEntry(int) -> waveform;
  port dac0;
  frame tx_frame_0 = newframe(dac0, 5700000000.0, 0);
  play(tx_frame_0, executeTableEntry(0));
}
defcal gate_1 $0 {
  delay[2400dt] tx_frame_0;
}
gate_1 $0;