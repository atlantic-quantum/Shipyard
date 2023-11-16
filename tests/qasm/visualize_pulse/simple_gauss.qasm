OPENQASM 3.0;

cal {
  port dac0;
  frame drive_frame = newframe(dac0, 7e9, 0);
  play(drive_frame, gauss(2000, 1.0, 1000, 250));
}