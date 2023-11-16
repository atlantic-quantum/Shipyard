OPENQASM 3.0;
int last_int = 0;
cal {
    int first_int = 3;
}
defcal dummy(int my_int) $0 {
    last_int = my_int + first_int;
}
int passing = 2;
dummy(passing) $0;