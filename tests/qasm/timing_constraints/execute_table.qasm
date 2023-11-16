OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
  extern executeTableEntry(int) -> waveform;
  port dac0;
  frame xy_frame_0 = newframe(dac0, 6400000000.0, 0);
  play(xy_frame_0, executeTableEntry(0));
}