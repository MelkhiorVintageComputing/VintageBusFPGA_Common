	.section .text.diagret
diagret:

	.section .text.loweritercount
loweritercount:
	.short 2	

	.section .text.Mconstop
Mconstop:
	jmp (%pc,diagret)
	
	.section .text.uart_time_const
uart_time_const:
	.byte 0x1e
	
	
