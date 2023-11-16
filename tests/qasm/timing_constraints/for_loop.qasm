//This test should pass warnings, even though second iteration of loop should 
//Fail test timing constraints 
OPENQASM 3.0;
defcalgrammar "openpulse";
const int n_steps = 3;
int dummy_num = 32;
cal {
  extern executeTableEntry(int) -> waveform;
  port dac0;
  frame xy_frame_0 = newframe(dac0, 6400000000.0, 0);
  for int i in [0:n_steps] {
    play(xy_frame_0, ones(dummy_num));
    dummy_num = dummy_num * 4;
}
}