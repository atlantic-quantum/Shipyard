OPENQASM 3.0;

cal {
  port dac0;
  frame drive_frame = newframe(dac0, 7e9, 0);
  set_phase(drive_frame, 1.0);
  for int i in [0:10] {
    shift_phase(drive_frame, -0.5);
    play(drive_frame, gauss(2000, 1.0, 1000, 250));
  }
}