	.section .text.fixIrq7Handler
	/* don't read the Memory Error Register in the Lvl 7 Interrupt Handler */
	/* this is the most likely to reapper in an operating system... */
fixIrq7Handler:
	move.b  #0,%d0
	nop
	

	.section .text.fixMonReset
	/* don't bother initializing the parity */
fixMonReset:
	nop
	nop
	nop
	nop

	.section .text.bypassTest0Eand0Fpatch
	/* bypass test_0E (parity memory error test)
	      and test_0F (forced parity error test)
	*/
bypassTest0Eand0Fpatch:
	jmp (%pc,memory_sizing_print)
	nop

	.section .text.memory_sizing_print
memory_sizing_print:	

	.section .text.check_sw:
check_sw:
	
	.section .text.test_10_memory_test
test_10_memory_test:	

	.section .text.patch_test_10_memory_test_1
	/* don't bother setting the register */
patch_test_10_memory_test_1:
	nop
	nop
	nop
	nop

	.section .text.patch_test_10_memory_test_2
	/* wipe out the code testing the registers and resetting them */
patch_test_10_memory_test_2:
	nop
	nop
	nop
	nop
	nop

	nop
	nop
	nop
	nop
	nop
	
	nop
	nop
	nop
	nop
	nop

	nop
	nop
	nop
	
	/* there is a read of the register in the case MEMERR in commands.c::monitor(), but that shouldn't happen without the hardware as no irq will be raised ? */

	.section .text.fixMonitor_Key_K
	/* when resetting with 'k', the parity control is cleared */
fixMonitor_Key_K:
	nop
	nop
	nop
	
