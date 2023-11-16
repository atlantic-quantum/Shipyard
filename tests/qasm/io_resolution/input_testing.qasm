OPENQASM 3.0;
defcalgrammar "openpulse";

//inputs:

input duration time_delta;
input int[4] n_shots;
input float f;
input bool b;
input bit bi;
input bit[2] second_bi;
input uint u;

duration zero = time_delta;
int one = n_shots;
float two = f;
bool three = b;
bit four = bi;
bit five = second_bi[0];
uint six = u;

zero=zero;
one = one;
two = two;
three = three;
four = four;
five = five;
six = six;