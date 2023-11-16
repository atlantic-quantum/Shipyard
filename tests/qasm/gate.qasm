OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port ch1;
  frame xy_frame_0 = newframe(ch1, 6400000000.0, 0);
}
defcal x90 $0 {
  play(xy_frame_0, gauss(32, 1.0, 16, 8) * 0.2063);
}
x90 $0;