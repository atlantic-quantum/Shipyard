OPENQASM 3.0;
defcalgrammar "openpulse";

const duration ones_duration = 1024.0dt;
const int i = 2;

cal {
    port ch1;
    frame frame2 = newframe(ch1, 0, 0);
    play(frame2, ones(ones_duration));
    play(frame2, ones(ones_duration * i));
    play(frame2, ones(i * ones_duration));
}