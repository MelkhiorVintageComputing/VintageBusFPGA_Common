	.section .text.replace1
replace1:
	cmp.l #0x08000000,%A5
	.section .text.finishedreplace1
	
	.section .text.replace2
replace2:
	move.l #0x01fe0000,%D5
	.section .text.finishedreplace2
