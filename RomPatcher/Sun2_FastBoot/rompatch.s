	.section .text.diagret
diagret:

	.section .text.loweritercount
loweritercount:
	.short 2	

	.section .text.Mconstop
Mconstop:
	jmp (%pc,diagret)
	
