OPENQASM 3.0;
defcalgrammar "openpulse";
const duration start_time = 32.0dt;
const duration time_step = 32.0dt;
const int n_steps = 63;
const int n_shots = 2000;
const duration capture_time = 12000.0dt;
const float qubit_frequency = -400000000.0;
const float drive_amplitude = 0;
const duration wait_time = 4000.0dt;
cal {
  port dac2;
  frame spec_frame = newframe(dac2, 4000000000.0, 0);
  delay[400dt] spec_frame;
  set_frequency(spec_frame, qubit_frequency);
}
cal {
  barrier;
  for int i in [0:n_steps] {
    for int j in [0:n_shots] {
      play(spec_frame, ones(start_time + i * time_step) * drive_amplitude);
      delay[48dt] spec_frame;
      delay[capture_time] spec_frame;
      delay[wait_time] spec_frame;
    }
  }
}
