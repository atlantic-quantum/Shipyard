OPENQASM 3.0;
defcalgrammar "openpulse";
cal {
  port ch1;
  frame lab_frame = newframe(ch1, 0, 0);
  waveform w_gauss = gauss(640dt, 1.0, 320dt, 50dt);
  let w_rise = w_gauss[0:319];
  let w_fall = w_gauss[320:639];
  waveform w_flat = rect(320, 1.0);
  let w_pulse = w_rise ++ w_flat ++ w_fall;

  int i = 0;
  while (i < 5) {
    play(lab_frame, w_pulse);
    i = i + 1;
  }
}
