## =============================================================================
## Constraint File (XDC) for Edge Artix-7 FPGA Board (XC7A35T-1FTG256C)
## Project: Real-Time Zebra Crossing Detection System
## Reference: D:\Downloads\board_master.xdc
## =============================================================================

# -----------------------------------------------------------------------------
# 50 MHz On-Board Oscillator Clock
# -----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN N11 IOSTANDARD LVCMOS33 } [get_ports { clk_50mhz }]
create_clock -add -name sys_clk_pin -period 20.00 -waveform {0 10} [get_ports { clk_50mhz }]

# -----------------------------------------------------------------------------
# Push Button Reset (Center Button - Active High with Pulldown)
# -----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN M14 IOSTANDARD LVCMOS33 PULLDOWN true } [get_ports { rst }]

# -----------------------------------------------------------------------------
# USB-UART Interface (FTDI Bridge)
# C4 = TXD (FPGA -> PC), D4 = RXD (PC -> FPGA)
# -----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN D4 IOSTANDARD LVCMOS33 } [get_ports { uart_rx }]
set_property -dict { PACKAGE_PIN C4 IOSTANDARD LVCMOS33 } [get_ports { uart_tx }]

# -----------------------------------------------------------------------------
# On-Board Status LEDs
# -----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN J3 IOSTANDARD LVCMOS33 } [get_ports { led_receiving }]
set_property -dict { PACKAGE_PIN H3 IOSTANDARD LVCMOS33 } [get_ports { led_processing }]
set_property -dict { PACKAGE_PIN J1 IOSTANDARD LVCMOS33 } [get_ports { led_detected }]
set_property -dict { PACKAGE_PIN K1 IOSTANDARD LVCMOS33 } [get_ports { led_error }]

# -----------------------------------------------------------------------------
# 7-Segment Display (Multiplexed 4-Digit Display)
# -----------------------------------------------------------------------------
set_property -dict { PACKAGE_PIN F2 IOSTANDARD LVCMOS33 } [get_ports { digit_en[0] }]
set_property -dict { PACKAGE_PIN E1 IOSTANDARD LVCMOS33 } [get_ports { digit_en[1] }]
set_property -dict { PACKAGE_PIN G5 IOSTANDARD LVCMOS33 } [get_ports { digit_en[2] }]
set_property -dict { PACKAGE_PIN G4 IOSTANDARD LVCMOS33 } [get_ports { digit_en[3] }]

set_property -dict { PACKAGE_PIN G2 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[0] }]
set_property -dict { PACKAGE_PIN G1 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[1] }]
set_property -dict { PACKAGE_PIN H5 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[2] }]
set_property -dict { PACKAGE_PIN H4 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[3] }]
set_property -dict { PACKAGE_PIN J5 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[4] }]
set_property -dict { PACKAGE_PIN J4 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[5] }]
set_property -dict { PACKAGE_PIN H2 IOSTANDARD LVCMOS33 } [get_ports { Seven_Seg[6] }]

# -----------------------------------------------------------------------------
# Timing Constraints & False Paths
# -----------------------------------------------------------------------------
set_false_path -from [get_ports uart_rx]
set_false_path -to   [get_ports uart_tx]
set_false_path -to   [get_ports led_*]
set_false_path -to   [get_ports digit_en*]
set_false_path -to   [get_ports Seven_Seg*]
set_false_path -from [get_ports rst]

# Configuration options for Artix-7 bitstream generation
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
