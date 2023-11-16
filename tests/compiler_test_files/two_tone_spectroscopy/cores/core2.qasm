OPENQASM 3.0;
defcalgrammar "openpulse";
const float frequency_start = -750000000.0;
const float frequency_step = 15000000.0;
const int n_steps = 100;
cal {
  port dac0;
  frame spec_frame = newframe(dac0, 5000000000.0, 0);
}
defcal measure_resonator $0 {
  delay[2016dt] spec_frame;
}
barrier;
cal {
  for int i in [0:n_steps] {
    delay[512dt] spec_frame;
    set_frequency(spec_frame, frequency_start + i * frequency_step);
    play(spec_frame, ones(2016dt));
    measure_resonator $0;
  }
}