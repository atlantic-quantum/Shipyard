OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port dac0;
  frame frame_0 = newframe(dac0, 0, 0);
}
defcal x $0 {
  play(frame_0, ones(2400dt) * 0.2);
}
defcal measure $0 {
  delay[4800dt] frame_0;
}
barrier;
x $0;
measure $0;