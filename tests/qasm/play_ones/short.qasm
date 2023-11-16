OPENQASM 3.0;
defcalgrammar "openpulse";

cal {
    port ch1;
    frame frame2 = newframe(ch1, 0, 0);
    play(frame2, ones(32dt));
    play(frame2, ones(256dt));
}