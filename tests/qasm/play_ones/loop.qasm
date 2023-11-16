OPENQASM 3.0;
defcalgrammar "openpulse";

const duration ones_duration = 1024.0dt;

cal {
    port ch1;
    frame frame2 = newframe(ch1, 0, 0);
    for int i in [1:10] {
        play(frame2, ones(ones_duration * i));
    }

    for int k in [1:10] {
        play(frame2, ones(ones_duration));
    }

    for int j in [0:10] {
        play(frame2, ones(ones_duration * j));
    }
}