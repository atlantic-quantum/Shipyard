OPENQASM 3.0;
def subtract_four(int a){
    return a - 4;
}
def adder(int a, int b){
    int c = a + b + 4;
    c = subtract_four(c);
    return c;
}
int dummy = adder(6,10);