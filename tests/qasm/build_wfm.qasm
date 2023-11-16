OPENQASM 3.0;
defcalgrammar "openpulse";

const int N = 1024;
const int width = 100;
const int position = N/2;
const float f_start = 0.1;
const float f_stop = 0.2;

array[float, N] w_array;

for int i in [0:N] {
  w_array[i] = sin(10/(cosh((i-position)/width)));
}

cal {
  port ch1;
  frame lab_frame = newframe(ch1, 0, 0);
  play(lab_frame, w_array);
}