OPENQASM 3.0;
int n_shots = 3;
int n_steps = 2;
int counter = 0;
for int j in [0:n_shots] {
    for int i in [0:n_steps] {
        counter = counter + 1;
    }
}