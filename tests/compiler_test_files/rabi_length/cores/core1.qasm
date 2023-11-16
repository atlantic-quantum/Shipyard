OPENQASM 3.0;
defcalgrammar "openpulse";
const int n_steps = 63;
const int n_shots = 2000;
cal {
}
cal {
  barrier;
  for int i in [0:n_steps] {
    for int j in [0:n_shots] {
    }
  }
}