	MAPBASE=0x20000000
	MAPSIZE=0x0f000000
	MAPEND=MAPBASE+MAPSIZE

/* ************************************************************************ */
	/* updated table */
	.section .text.raminfo
	.long MAPBASE
	.long MAPEND
	.long 0x04000000
	.long 0x08000000
	.long 0x00000000
	.long 0x04000000
	.long 0xFFFFFFFF
	.long 0xFFFFFFFF
	
/* ************************************************************************ */
	.section .text.gary
fixchunk:			/* 316 bytes available */
	/*  recreate the table but with one more chunk, as the original code assumes two chunks and turns them into three */
	
	move.l %D4,(%A1)+
	move.l %D5,(%A1)+
	move.l %D2,(%A1)+
	move.l %D3,(%A1)+
	
	add.l %D5,%D4
	move.l %D4,(%A1)+
	move.l %D1,(%A1)+
	
	/* here comes the bonus */
	move.l #MAPBASE,(%A1)+
	move.l #MAPSIZE,(%A1)+
	/* here ends the bonus */
	
	moveq #-1,%D4
	move.l %D4,(%A1)+
	move.l %D4,(%A1)+
	
	jmp (%pc,returnfindinfopatch)
	
/* ************************************************************************ */
	.section .text.findinfopatch
findinfopatch:				/* 20 bytes available */
	jmp (%pc,fixchunk)
	
	.section .text.returnfindinfopatch
returnfindinfopatch:	
	/* */

	.end
