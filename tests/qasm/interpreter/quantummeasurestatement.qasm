OPENQASM 3.0;
defcalgrammar "openpulse";

bit b = 0;
bit[2] bit_reg;


defcal measure $0 -> int {
    int c = 3;
    return c;
}

barrier;

b = measure $0;
bit_reg[0] = measure $0;