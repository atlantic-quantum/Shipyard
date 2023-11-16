OPENQASM 3.0;

cal {
  port dac0;
  frame drive_frame = newframe(dac0, 7e9, 0);
  for int i in [0:5] {
    play(drive_frame, (i+1) / 5 * gauss(2000, 1.0, 1000, 250));
  }
}