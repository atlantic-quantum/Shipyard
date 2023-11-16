OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  extern executeTableEntry(int) -> waveform;
  port dac1;
  frame flux_bias = newframe(dac1, 0, 0);
}
defcal gate_1 $0 {
  play(flux_bias, executeTableEntry(2));
}
gate_1 $0;
