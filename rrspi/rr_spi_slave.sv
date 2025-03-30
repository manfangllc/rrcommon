module rr_spi_slave #(
    parameter CMD_WIDTH = 16,          // Command width in bits
    parameter DATA_WIDTH = 8           // Data width in bits
) (
    // System signals
    input  logic clk,                  // System clock
    input  logic rst_n,                // Active low reset
    
    // SPI signals
    input  logic sclk,                 // SPI clock from master
    input  logic mosi,                 // Master Out Slave In
    input  logic cs_n,                 // Chip Select (active low)
    output logic miso,                 // Master In Slave Out (tri-state)
    
    // Control and data signals
    output logic cmd_received,         // Command received indicator
    output logic [CMD_WIDTH-1:0] cmd,  // Received command
    output logic [DATA_WIDTH-1:0] rx_data, // Received data
    input  logic [DATA_WIDTH-1:0] tx_data, // Data to transmit
    output logic transfer_done         // Transfer complete indicator
);

    // State machine definition
    typedef enum logic [1:0] {
        IDLE,
        COMMAND,
        DATA
    } spi_state_t;
    
    spi_state_t state, next_state;
    
    // Edge detection for SCLK
    logic sclk_dly, sclk_rising, sclk_falling;
    logic cs_n_dly, cs_n_rising, cs_n_falling;
    
    // Internal counters and registers
    logic [$clog2(CMD_WIDTH)-1:0] cmd_count;
    logic [$clog2(DATA_WIDTH)-1:0] data_count;
    logic [CMD_WIDTH-1:0] cmd_reg;
    logic [DATA_WIDTH-1:0] rx_reg, tx_reg;
    logic miso_out;
    
    // Edge detection logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_dly <= 1'b1;
            cs_n_dly <= 1'b1;
        end else begin
            sclk_dly <= sclk;
            cs_n_dly <= cs_n;
        end
    end
    
    assign sclk_rising = sclk && !sclk_dly;
    assign sclk_falling = !sclk && sclk_dly;
    assign cs_n_rising = cs_n && !cs_n_dly;
    assign cs_n_falling = !cs_n && cs_n_dly;
    
    // State machine - sequential part
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
        end else begin
            state <= next_state;
        end
    end
    
    // State machine - combinational part
    always_comb begin
        next_state = state;
        
        case (state)
            IDLE: begin
                if (cs_n_falling)
                    next_state = COMMAND;
            end
            
            COMMAND: begin
                if (cs_n_rising)
                    next_state = IDLE;
                else if (cmd_count == CMD_WIDTH-1 && sclk_rising)
                    next_state = DATA;
            end
            
            DATA: begin
                if (cs_n_rising)
                    next_state = IDLE;
            end
            
            default: next_state = IDLE;
        endcase
    end
    
    // Control signals and data handling
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cmd_count <= '0;
            data_count <= '0;
            cmd_reg <= '0;
            rx_reg <= '0;
            tx_reg <= '0;
            cmd <= '0;
            rx_data <= '0;
            cmd_received <= 1'b0;
            transfer_done <= 1'b0;
            miso_out <= 1'b0;
        end else begin
            // Default values
            cmd_received <= 1'b0;
            transfer_done <= 1'b0;
            
            case (state)
                IDLE: begin
                    cmd_count <= '0;
                    data_count <= '0;
                end
                
                COMMAND: begin
                    // Sample MOSI on rising edge of SCLK
                    if (sclk_rising) begin
                        cmd_reg <= {cmd_reg[CMD_WIDTH-2:0], mosi};
                        cmd_count <= cmd_count + 1'b1;
                        
                        if (cmd_count == CMD_WIDTH-1) begin
                            cmd <= {cmd_reg[CMD_WIDTH-2:0], mosi};
                            cmd_received <= 1'b1;
                            tx_reg <= tx_data;  // Load transmit data after command is received
                        end
                    end
                    
                    // Reset on CS rising
                    if (cs_n_rising) begin
                        cmd_count <= '0;
                    end
                end
                
                DATA: begin
                    // Update MISO on falling edge of SCLK
                    if (sclk_falling) begin
                        miso_out <= tx_reg[DATA_WIDTH-1];
                        tx_reg <= {tx_reg[DATA_WIDTH-2:0], 1'b0};
                    end
                    
                    // Sample MOSI on rising edge of SCLK
                    if (sclk_rising) begin
                        rx_reg <= {rx_reg[DATA_WIDTH-2:0], mosi};
                        data_count <= data_count + 1'b1;
                        
                        if (data_count == DATA_WIDTH-1) begin
                            rx_data <= {rx_reg[DATA_WIDTH-2:0], mosi};
                            transfer_done <= 1'b1;
                        end
                    end
                    
                    // Reset on CS rising
                    if (cs_n_rising) begin
                        rx_data <= {rx_reg[DATA_WIDTH-2:0], mosi};
                        data_count <= '0;
                        transfer_done <= 1'b1;
                    end
                end
            endcase
        end
    end
    
    // Drive MISO output (tri-state when not selected or not in DATA state)
    assign miso = (state == DATA && !cs_n) ? miso_out : 1'bz;

endmodule