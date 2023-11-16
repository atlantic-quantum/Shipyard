OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
  port dac3;
  port adc0;
  port dac0;
  port dac1;
  port dac2;
  frame xy_frame_0 = newframe(dac0, 6400000000.0, 0);
  frame tx_frame_1 = newframe(dac3, 5800000000.0, 0);
  frame rx_frame_1 = newframe(adc0, 5800000000.0, 0);
  frame xy_frame_1 = newframe(dac1, 6500000000.0, 0);
  frame tx_frame_2 = newframe(dac3, 5900000000.0, 0);
  frame rx_frame_2 = newframe(adc0, 5900000000.0, 0);
  frame xy_frame_2 = newframe(dac2, 6600000000.0, 0);
  waveform w_gauss = 1.0*gauss(8001dt, 1.0, 4000dt, 1000dt);
  play(xy_frame_0, w_gauss);
}

def dummy_func() ->int {
    const int dummy_var = 2401;
    return dummy_var;
}

bit feedback_bit;

defcal measure $1 -> bit {
  play(tx_frame_1, ones(2400dt)*0.2);
  return capture_v2(rx_frame_1, ones(dummy_func()));
}

feedback_bit = measure $1;