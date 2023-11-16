OPENQASM 3.0;

cal {
  port dac0;
  frame drive_frame = newframe(dac0, 7e9, 0);
  shift_frequency(drive_frame, 100e6);
  play(drive_frame, 0*ones(2000));
  for int i in [0:5] {
    set_frequency(drive_frame, 7.2e9 + i * 100e6);
    play(drive_frame, gauss(2000, 1.0, 1000, 250));
  }
}