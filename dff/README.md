# D Flip-Flop Module

A parameterized D flip-flop with synchronous reset.

## Ports

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| clk  | input     | 1     | Clock input |
| rst_n| input     | 1     | Active-low reset |
| d_i  | input     | DATA_WIDTH | Data input |
| q_o  | output    | DATA_WIDTH | Data output |

## Parameters

| Parameter    | Default | Description |
|-------------|---------|-------------|
| DATA_WIDTH  | 1       | Width of data input and output |

## Instantiation Example

```systemverilog
dff #(
    .DATA_WIDTH(8)
) dff_inst (
    .clk(clk),
    .rst_n(rst_n),
    .d_i(data_in),
    .q_o(data_out)
);
```

## Module Usage

The D flip-flop captures the input data on the rising edge of the clock and holds it until the next rising edge. The output is synchronously reset to zero when the active-low reset signal is asserted.

## Timing Diagram

```
clk    __|--|__|--|__|--|__|--|__|--|__|--|__|--|__|--|__
rst_n  ________|--|_______________________________________
d_i    XXXX 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1
q_o    XXXX 0 0 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1
```

Legend:
- X: Don't care
- 0: Logic low
- 1: Logic high
- |: Rising clock edge
- --: Falling clock edge 