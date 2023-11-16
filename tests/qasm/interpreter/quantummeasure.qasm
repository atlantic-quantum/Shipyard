OPENQASM 3.0;
int dummy_var = 0;
defcal measure $0 {
    dummy_var = 3;
}
measure $0;