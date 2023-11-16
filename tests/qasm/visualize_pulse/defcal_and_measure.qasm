OPENQASM 3.0;

const duration drive_time = 320dt;
const float drive_amplitude = 1.0;
const duration capture_time = 160dt;
const float resonator_ampitude = 0.65;

cal {
  port dac0;
  port adc0;
  port dac1;
  frame rx_frame = newframe(adc0, 7e9, 0);
  frame tx_frame = newframe(dac0, 7e9, 0);
  frame drive_frame = newframe(dac1, 4e9, 0);
}

defcal x $0 {
  play(drive_frame, drive_amplitude * gauss(drive_time, 1.0, 1.5*drive_time, drive_time/2));
  delay[3*drive_time] tx_frame, rx_frame; //is this legal?
}

defcal measure $0 {
  delay[192dt] drive_frame;
  let first_alias = sine(16, 1.0, 0, 0.25) ++ ones(160) ++ sine(16, 1.0, 3.14/2, 0.25);
  play(tx_frame, resonator_ampitude * first_alias);
  let second_alias = sine(16, 1.0, 0, 0.25) ++ ones(160) ++ sine(16, 1.0, 3.14/2, 0.25);
  capture_v1(rx_frame, second_alias);
}

x $0;
measure $0;