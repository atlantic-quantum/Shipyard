OPENQASM 3.0;
int dummy_var = 0;
defcal reset $0 {
    dummy_var = 3;
}
reset $0;