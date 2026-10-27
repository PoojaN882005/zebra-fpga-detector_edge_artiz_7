open_project {D:/Downloads/Raj/Zebra_final_try/Zebra_final_try.xpr}
reset_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
puts "=== BITSTREAM GENERATION STATUS ==="
puts "impl_1 status: [get_property STATUS [get_runs impl_1]]"
puts "impl_1 progress: [get_property PROGRESS [get_runs impl_1]]"
close_project
