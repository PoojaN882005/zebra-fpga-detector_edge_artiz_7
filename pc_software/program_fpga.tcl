open_hw_manager
connect_hw_server -allow_non_jtag
open_hw_target
set hw_devices [get_hw_devices]
puts "CONNECTED_DEVICES: $hw_devices"
if {[llength $hw_devices] > 0} {
    set hw_dev [lindex $hw_devices 0]
    puts "PROGRAMMING_DEVICE: $hw_dev"
    set_property PROGRAM.FILE {D:/Downloads/Raj/Zebra_final_try/Zebra_final_try.runs/impl_1/zebra_top.bit} $hw_dev
    program_hw_devices $hw_dev
    puts "=== FPGA PROGRAMMED SUCCESSFULLY ==="
} else {
    puts "NO_DEVICES_FOUND"
}
close_hw_target
close_hw_manager
