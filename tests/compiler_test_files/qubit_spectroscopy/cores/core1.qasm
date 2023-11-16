OPENQASM 3.0;
defcalgrammar "openpulse";
const int n_steps_freq = 40;
const float bias_start = -1.0;
const float bias_step = 0.04;
const int n_steps_flux = 50;
cal {
  port dac2;
  frame flux_bias = newframe(dac2, 0, 0);
}
barrier;
cal {
  for int j in [0:n_steps_flux] {
    for int i in [0:n_steps_freq] {
      play(flux_bias, (bias_start + j * bias_step) * ones(4448dt));
    }
  }
}