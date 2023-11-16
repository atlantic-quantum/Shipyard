OPENQASM 3.0;
int used = 1;
def used_function(int j) {
    used = j;
}
def unused_function(int j) {
    used = j;
}
used_function(3);