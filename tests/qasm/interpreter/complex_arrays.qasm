// testing complex arrays and array indexing
OPENQASM 3.0;
int dummy = 4;
array [int, 3, 2] two_d = {{1, 2}, {3,4}, {5,6}};
array[complex, 3] my_arr = {1 + 0 im, 0 + 1 im, 0.8 + 0.6 im};
array [int, 4] second = {1,2,3,dummy};
