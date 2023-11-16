OPENQASM 3.0;
defcalgrammar "openpulse";
const float frequency_start = -750000000.0;
const float frequency_step = 30000000.0;
const int n_steps_freq = 40;
const int n_steps_flux = 50;
cal {
  port dac0;
  frame spec_frame = newframe(dac0, 5000000000.0, 0);
}
defcal measure_resonator $0 {
  delay[2016dt] spec_frame;
}
barrier;
cal {
  for int j in [0:n_steps_flux] {
    for int i in [0:n_steps_freq] {
      delay[416dt] spec_frame;
      set_frequency(spec_frame, frequency_start + i * frequency_step);
      play(spec_frame, ones(2016dt));
      measure_resonator $0;
    }
  }
}