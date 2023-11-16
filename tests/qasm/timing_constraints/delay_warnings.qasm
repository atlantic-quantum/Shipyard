OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
    port dac0;
    frame my_frame = newframe(dac0, 0, 0);
    delay[0.0ns] my_frame;

    delay[1.0ns] my_frame;

    delay[17.0ns] my_frame;

    duration some_dur = 31.0ns;

    delay[some_dur] my_frame;
}
