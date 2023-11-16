OPENQASM 3.0;
defcalgrammar "openpulse";
// this example includes a more complicated relative path

include "../../qasm/include_files/included_3.inc";
//include "included_3.inc";
include "included_4.qasm";


for int j in [0:n_shots] {
    for int i in [0:n_steps] {
        duration delay_time = time_start + i * time_delta;
        xhalf $0;
        delay_0(delay_time) $0;
        xhalf $0;
        measure $0;
        reset $0;
    }
}