# RR Adder Module

A parameterized full adder module that can be used for single-bit or multi-bit addition operations.

## Ports

| Port Name | Direction | Width | Description |
|-----------|-----------|-------|-------------|
| a_i       | Input     | DATA_WIDTH | First input operand |
| b_i       | Input     | DATA_WIDTH | Second input operand |
| cin_i     | Input     | DATA_WIDTH | Carry input |
| sum_o     | Output    | DATA_WIDTH | Sum output |
| cout_o    | Output    | DATA_WIDTH | Carry output |

## Parameters

| Parameter Name | Default | Description |
|----------------|---------|-------------|
| DATA_WIDTH    | 1       | Width of input and output operands |

## Instantiation Example

```systemverilog
rr_adder #(
    .DATA_WIDTH(1)  // Set to 1 for single-bit, or N for N-bit addition
) u_rr_adder (
    .a_i(a),
    .b_i(b),
    .cin_i(cin),
    .sum_o(sum),
    .cout_o(cout)
);
```

## Module Usage Description

The RR Adder module implements a full adder circuit that can be used for both single-bit and multi-bit addition operations. It takes two input operands (a_i and b_i) and a carry input (cin_i), producing a sum output (sum_o) and a carry output (cout_o).

The module is parameterized by DATA_WIDTH, allowing it to be used for both single-bit and multi-bit operations. When DATA_WIDTH is set to 1, it functions as a traditional full adder. For larger values, it performs parallel addition on multiple bits.

## Example with Timing Diagram

```
Single-bit Full Adder Operation:

Time    a_i  b_i  cin_i  sum_o  cout_o
0ns     0    0    0      0      0
10ns    0    0    1      1      0
20ns    0    1    0      1      0
30ns    0    1    1      0      1
40ns    1    0    0      1      0
50ns    1    0    1      0      1
60ns    1    1    0      0      1
70ns    1    1    1      1      1
``` 