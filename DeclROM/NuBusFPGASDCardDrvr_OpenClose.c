#if defined(ENABLE_SDCARD)

#include "NuBusFPGASDCardDrvr.h"

#include <Disks.h>
#include <OSUtils.h>
#include <Events.h>

/* NuBusFPGA only supports 32-bits mode (the large framebuffer requires it),
   so the Prime/Control/Status routines don't switch the MMU mode */

/* FYI, missing in library with Retro68 */
/* void AddDrive(short drvrRefNum, short drvNum, DrvQElPtr qEl); */

/* re-implement with Retro68 features */
/* drVNum to high-order bits of num, drvrRefNum in low-order */
/* not sure how to do "parameter" without output ? */
#pragma parameter __D0 AddDrive(__D0, __A0)
__attribute__ ((section (".text.sddriver"))) static inline int dupAddDrive(unsigned long num, DrvQElPtr qEl) {
	/* the trap takes its arguments in D0 and A0 specifically: plain "d"/"a" constraints
	   let GCC pick any data/address register (it used A6 for qEl, so the trap got a
	   stale A0 and added a bogus drive queue element) */
	register unsigned long d0 asm("d0") = num;
	register DrvQElPtr a0 asm("a0") = qEl;
	asm volatile(".word 0xA04E" : "+d" (d0), "+a" (a0) : : "cc", "memory");
	return d0;
}

static int sdcard_init(struct SDCardContext* ctx) __attribute__ ((section (".text.sddriver")));

/* Drive/media icon for Control csCode 21/22, a micro-SD card:
                                   |
                                   |
       #####################       |
       #                   #       |
       #  # # # # # # # #  #       |
       #  # # # # # # # #  #       |
       #  # # # # # # # #  #       |
       #  # # # # # # # #  #       |
       #  # # # # # # # #  #       |
       #                   #       |
       #                   #       |
       #                   ##      |
       #                    ##     |
       #                     #     |
       #                     #     |
       #                     #     |
       #                     #     |
       #     #####  ####     #     |
       #    ##      ## ##    #     |
       #    ##      ##  ##   #     |
       #     ####   ##  ##   #     |
       #        ##  ##  ##   #     |
       #        ##  ## ##    #     |
       #    #####   ####     #     |
       #                     #     |
       #                     #     |
       #                     #     |
       #                     #     |
       #                     #     |
       #######################     |
                                   |
                                   |
   followed by its mask (the filled outline). It must be in the driver block (copied to
   RAM by the Slot Manager), but GCC won't put const data in a code section ("section
   type conflict"), so it's emitted with asm; -mpcrel makes references PC-relative. */
asm(".section .text.sddriver\n"
    "\t.even\n"
    "\t.global sdcard_icon\n"
    "sdcard_icon:\n"
	".byte 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0F,0xFF,0xFF,0x80,0x08,0x00,0x00,0x80\n"
	".byte 0x09,0x55,0x54,0x80,0x09,0x55,0x54,0x80,0x09,0x55,0x54,0x80,0x09,0x55,0x54,0x80\n"
	".byte 0x09,0x55,0x54,0x80,0x08,0x00,0x00,0x80,0x08,0x00,0x00,0x80,0x08,0x00,0x00,0xC0\n"
	".byte 0x08,0x00,0x00,0x60,0x08,0x00,0x00,0x20,0x08,0x00,0x00,0x20,0x08,0x00,0x00,0x20\n"
	".byte 0x08,0x00,0x00,0x20,0x08,0x3E,0x78,0x20,0x08,0x60,0x6C,0x20,0x08,0x60,0x66,0x20\n"
	".byte 0x08,0x3C,0x66,0x20,0x08,0x06,0x66,0x20,0x08,0x06,0x6C,0x20,0x08,0x7C,0x78,0x20\n"
	".byte 0x08,0x00,0x00,0x20,0x08,0x00,0x00,0x20,0x08,0x00,0x00,0x20,0x08,0x00,0x00,0x20\n"
	".byte 0x08,0x00,0x00,0x20,0x0F,0xFF,0xFF,0xE0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00\n"
	".byte 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0x80\n"
	".byte 0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0x80\n"
	".byte 0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0x80,0x0F,0xFF,0xFF,0xC0\n"
	".byte 0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0\n"
	".byte 0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0\n"
	".byte 0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0\n"
	".byte 0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0\n"
	".byte 0x0F,0xFF,0xFF,0xE0,0x0F,0xFF,0xFF,0xE0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00\n"
    "\t.global sdcard_where\n"
    "sdcard_where:\n" /* "Where:" string prefix, slot digit appended in Open */
    "\t.ascii \"NuBusFPGA micro-SD, slot $\"\n"
    "\t.global sdcard_where_end\n"
    "sdcard_where_end:\n"
    "\t.even\n"
    "\t.previous\n");
extern const unsigned char sdcard_icon[256];
extern const char sdcard_where[], sdcard_where_end[]; /* in the driver block too, not .rodata */

#include <ROMDefs.h>

#pragma parameter __D0 cNuBusFPGASDCardOpen(__A0, __A1)
OSErr cNuBusFPGASDCardOpen(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce)
{
	DrvSts2 *dsptr; // pointer to the DrvSts2 in our context
	int drvnum = 1;
	struct SDCardContext *ctx;
	OSErr ret = noErr;
	char busMode;
	char slot = dce->dCtlSlot;

	busMode = 1;
	SwapMMUMode ( &busMode ); // to32

	if (dce->dCtlDevBase == 0) { // no MinorBaseOS/MajorBaseOS in the sResource, so the Slot Manager leaves this empty
		if ((dce->dCtlSlot > 0xE) || (dce->dCtlSlot < 0x9)) { // safety net
			SpBlock				mySpBlock;
			SInfoRecord			mySInfoRecord;
			mySpBlock.spResult = (long)&mySInfoRecord;

			mySpBlock.spSlot = 0x9; // start at first
			mySpBlock.spID = 0;
			mySpBlock.spExtDev = 0;
			mySpBlock.spCategory = catProto;
			mySpBlock.spCType = 0x1000; // typeDrive;
			mySpBlock.spDrvrSW = drSwApple;
			mySpBlock.spDrvrHW = 0xbeec; // DrHwNuBusFPGASDCard
			mySpBlock.spTBMask = 0;
			ret = SNextTypeSRsrc(&mySpBlock);
			if (ret)
				goto done;
			slot = mySpBlock.spSlot;
		}
		dce->dCtlDevBase = 0xF0000000ul | ((unsigned long)slot << 24);
	}

	if (dce->dCtlStorage == nil) {
		DrvQElPtr dq;
		for(dq = (DrvQElPtr)(GetDrvQHdr())->qHead; dq; dq = (DrvQElPtr)dq->qLink) {
			if (dq->dQDrive >= drvnum)
				drvnum = dq->dQDrive+1;
		}

		ReserveMemSys(sizeof(struct SDCardContext));
		dce->dCtlStorage = NewHandleSysClear(sizeof(struct SDCardContext));
		if (dce->dCtlStorage == nil) {
			ret = openErr;
			goto done;
		}

		HLock(dce->dCtlStorage);

		ctx = *(struct SDCardContext **)dce->dCtlStorage;
		ctx->slot = slot;
		ctx->sc = dce->dCtlDevBase;

		/* init the SDCard, this will also fill out ctx->size_blk */
		if (!sdcard_init(ctx)) {
			ret = openErr;
			HUnlock(dce->dCtlStorage);
			DisposeHandle(dce->dCtlStorage);
			dce->dCtlStorage = NULL;
			goto done;
		}

		/* icon + mask + "Where:" string, for Control csCode 21/22 */
		BlockMoveData(sdcard_icon, ctx->icon, 256);
		{
			unsigned char *w = ctx->icon + 256;
			int i;
			for (i = 0 ; &sdcard_where[i] < sdcard_where_end ; i++)
				w[1 + i] = sdcard_where[i];
			w[1 + i] = (slot < 10) ? ('0' + slot) : ('A' + slot - 10);
			w[0] = i + 1;
		}

		dsptr = &ctx->drvsts;
		// dsptr->track /* current track */
		dsptr->writeProt = 0; /* bit 7 = 1 if volume is locked */
		dsptr->diskInPlace = 8; /* disk in drive, non-ejectable */
		dsptr->installed = 1; /* drive installed */
		// dsptr->sides /* -1 for 2-sided, 0 for 1-sided */
		// dsptr->QLink /* next queue entry */
		dsptr->qType = 1; /* 1 for HD20 */ /* Files 2-85 (p173) : 1 to enable S1 */
		dsptr->dQDrive = drvnum; /* drive number */
		dsptr->dQRefNum = dce->dCtlRefNum; /* driver reference number */
		// dsptr->dQFSID /* file system ID */
		dsptr->driveSize = ctx->size_blk & 0x0000FFFFul;
		dsptr->driveS1 = (ctx->size_blk & 0xFFFF0000ul) >> 16;
		// dsptr->driveType
		// dsptr->driveManf
		// dsptr->driveChar
		// dsptr->driveMisc

		// add the drive
		dupAddDrive((dsptr->dQRefNum & 0xFFFF) | (drvnum << 16), (DrvQElPtr)&dsptr->qLink);

		/* nothing else mounts it at startup: mount it now, as the RAM disk does.
		   Errors (e.g. blank/unformatted card) are ignored, so the driver stays open
		   and the volume can still be initialized or mounted later with a disk tool.
		   Not when opened by the sBootRecord's first call: that's early in the ROM
		   startup, the Start Manager mounts the startup volume itself (and the boot
		   record posts a disk-inserted event for the other case). */
		if (((SlotDevParamPtr)pb)->ioSMix != (Ptr)SDCARD_BOOT_MAGIC) {
			ParamBlockRec pbr;
			pbr.volumeParam.ioCompletion = NULL;
			pbr.volumeParam.ioVRefNum = dsptr->dQDrive;
			(void)PBMountVol(&pbr);
		}
	}

 done:
	SwapMMUMode ( &busMode );
	return ret;
}

#pragma parameter __D0 cNuBusFPGASDCardClose(__A0, __A1)
OSErr cNuBusFPGASDCardClose(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce)
{
	OSErr ret = noErr;

	if (dce->dCtlStorage) {
		struct SDCardContext *ctx = *(struct SDCardContext**)dce->dCtlStorage;
		/* the drive queue element lives in our storage, remove it before freeing */
		Dequeue((QElemPtr)&ctx->drvsts.qLink, GetDrvQHdr());
		/* HUnlock(dce->dCtlStorage); */ /* not needed before DisposeHandle */
		DisposeHandle(dce->dCtlStorage);
		dce->dCtlStorage = NULL;
	}
	return ret;
}

/*-----------------------------------------------------------------------*/
/* Helpers                                                               */
/*-----------------------------------------------------------------------*/

#define max(x, y) (((x) > (y)) ? (x) : (y))
#define min(x, y) (((x) < (y)) ? (x) : (y))

/* In MacOS
   Delay(unsigned long numTicks, unsigned long *  finalTicks)
   has ticks in 1/60th of a second or 16.6666 ms
*/

/* in NetBSD/sparc busy_wait is 1ms * d */
void busy_wait(int d) {
  waitSome(d * 20000); // improveme
  return;
}
/* in NetBSD/sparc delay is 1us * d */
void delay(int d) {
  waitSome(d * 20); // improveme
  return;
}

/*-----------------------------------------------------------------------*/
/* SDCard command helpers                                                */
/*-----------------------------------------------------------------------*/

/* NuBus writes are posted (acked immediately and queued), but reads go through the same
   request FIFO on the board, so a read always sees the effect of all earlier writes:
   no explicit fence needed (e.g. reading cmd_event right after writing cmd_send). */

/* TickCount() is a trap, so only check it every 256 iterations */
#define SD_TICKS_EXPIRED(i, start, max) ((((i) & 0xFF) == 0) && ((TickCount() - (start)) > (max)))

/* only valid once the command is done; the SD core only reports done when back to idle,
   i.e. after the data phase (including card busy after each written block) */
__attribute__ ((section (".text.sddriver"))) static int sdcard_wait_cmd_done(struct SDCardContext *ctx, unsigned long maxticks) {
	unsigned int event;
	unsigned long i;
	unsigned long maxpoll = maxticks << 16;
	unsigned long start = TickCount();
	for (i = 0 ; i < maxpoll ; i++) {
		event = sdcore_cmd_event_read(ctx->sc);
		if (event & 0x1) {
			if (event & 0x4)
				return SD_TIMEOUT;
			if (event & 0x8) /* never set by the current gateware */
				return SD_CRCERROR;
			return SD_OK;
		}
		if (SD_TICKS_EXPIRED(i, start, maxticks))
			break;
	}
	/* some states of the SD core/PHY have no hardware timeout, it's stuck for good */
	ctx->dead = 1;
	return SD_HWHANG;
}

/*-----------------------------------------------------------------------*/
/* SDCard clocker functions                                              */
/*-----------------------------------------------------------------------*/

/* divider must be a power of 2 between 2 and 256 (sys_clk/2 for anything else) */
void sdcard_set_divider(struct SDCardContext *ctx, uint32_t divider) {
	sdphy_clocker_divider_write(ctx->sc, divider);
	ctx->divider = divider;
	/* 8 SD clocks = 80 ns * divider; at >= 200 ns per NuBus read, divider/2 + 2 reads covers it */
	ctx->guard = (divider >> 1) + 2;
}

/*-----------------------------------------------------------------------*/
/* SDCard commands functions                                             */
/*-----------------------------------------------------------------------*/

__attribute__ ((section (".text.sddriver"))) static int sdcard_send_command(struct SDCardContext *ctx, uint32_t arg, uint8_t cmd, uint8_t rsp, unsigned long maxticks) {
	uint32_t sc = ctx->sc;
	int i;
	if (ctx->dead)
		return SD_HWHANG;
	/* let the PHY finish the trailing clocks of the previous response */
	for (i = 0 ; i < ctx->guard ; i++)
		(void)sdcore_cmd_event_read(sc);
	sdcore_cmd_argument_write(sc, arg);
	sdcore_cmd_command_write(sc, (cmd << 8) | rsp);
	sdcore_cmd_send_write(sc, 1);
	return sdcard_wait_cmd_done(ctx, maxticks);
}

/* short responses (R1, R3, R6, R7): the 32 bits between the command index and the CRC */
__attribute__ ((section (".text.sddriver"))) static inline uint32_t sdcard_response32(struct SDCardContext *ctx) {
	return __builtin_bswap32(*(volatile uint32_t*)(ctx->sc + CSR_SDCORE_CMD_RESPONSE_ADDR + 12));
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_go_idle(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, 0, 0, SDCARD_CTRL_RESPONSE_NONE, SD_TICKS_CMD);
}

/* CMD8, SEND_IF_COND (the LiteX code calls it send_ext_csd) */
__attribute__ ((section (".text.sddriver"))) static inline int sdcard_send_if_cond(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, 0x000001aa, 8, SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_app_cmd(struct SDCardContext *ctx, uint16_t rca) {
	return sdcard_send_command(ctx, rca << 16, 55, SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_app_send_op_cond(struct SDCardContext *ctx, int hcs) {
	uint32_t arg = 0x10ff8000;
	if (hcs)
		arg |= 0x60000000;
	return sdcard_send_command(ctx, arg, 41, SDCARD_CTRL_RESPONSE_SHORT_BUSY, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_all_send_cid(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, 0, 2, SDCARD_CTRL_RESPONSE_LONG, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_set_relative_address(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, 0, 3, SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_send_csd(struct SDCardContext *ctx, uint16_t rca) {
	return sdcard_send_command(ctx, rca << 16, 9, SDCARD_CTRL_RESPONSE_LONG, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_select_card(struct SDCardContext *ctx, uint16_t rca) {
	return sdcard_send_command(ctx, rca << 16, 7, SDCARD_CTRL_RESPONSE_SHORT_BUSY, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_app_set_bus_width(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, 2, 6, SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD);
}

/* the 64 bytes of switch status are DMA'd to sd_buf, to record whether the switch worked */
__attribute__ ((section (".text.sddriver"))) static int sdcard_switch(struct SDCardContext *ctx, unsigned int mode, unsigned int group, unsigned int value) {
	uint32_t sc = ctx->sc;
	unsigned int arg;
	unsigned long i;
	int res;
	arg = (mode << 31) | 0xffffff;
	arg &= ~(0xf << (group * 4));
	arg |= value << (group * 4);

	ctx->hs_status = 0xFFFF;
	sdblock2mem_dma_enable_write(sc, 0);
	(void)sdblock2mem_dma_enable_read(sc); /* ordered after the write: the DMA is disabled from now on */
	delay(50);
	sdblock2mem_dma_base_write(sc, SDCARD_BUF_DMA_ADDR);
	sdblock2mem_dma_length_write(sc, 64);
	sdblock2mem_dma_enable_write(sc, 1);

	sdcore_block_length_write(sc, 64);
	sdcore_block_count_write(sc, 1);
	res = sdcard_send_command(ctx, arg, 6,
				  (SDCARD_CTRL_DATA_TRANSFER_READ << 5) |
				  SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD + (1ul << SD_TICKS_PER_BLK_SHIFT));
	if ((res == SD_OK) && !(sdcore_data_event_read(sc) & 0x4)) {
		for (i = 0 ; i < SD_POLL_DMA ; i++) {
			if (sdblock2mem_dma_done_read(sc) & 0x1) {
				/* bits [379:376] of the 512-bit status: function selected in group 1 (0xF = error) */
				ctx->hs_status = *(volatile uint8_t*)(sc + SDCARD_BUF_OFFSET + 16) & 0xF;
				break;
			}
		}
	}
	sdblock2mem_dma_enable_write(sc, 0);
	return res;
}

/* switch between default speed (card outputs change after CLK falling edge) and High Speed
   (after the rising edge); hs_status records the card's answer (0 or 1, 0xF = refused) */
int sdcard_set_speed(struct SDCardContext *ctx, int hs) {
	return sdcard_switch(ctx, SD_SWITCH_SWITCH, SD_GROUP_ACCESSMODE, hs ? SD_SPEED_SDR25 : SD_SPEED_SDR12);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_set_blocklen(struct SDCardContext *ctx, unsigned int blocklen) {
	return sdcard_send_command(ctx, blocklen, 16, SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_stop_transmission(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, 0, 12, SDCARD_CTRL_RESPONSE_SHORT_BUSY, SD_TICKS_CMD);
}

__attribute__ ((section (".text.sddriver"))) static inline int sdcard_send_status(struct SDCardContext *ctx) {
	return sdcard_send_command(ctx, ctx->rca << 16, 13, SDCARD_CTRL_RESPONSE_SHORT, SD_TICKS_CMD);
}

/* CSD is the 128 bits of the long response, r[0] = CSD[127:96] ... r[3] = CSD[31:0] */
__attribute__ ((section (".text.sddriver"))) static int sdcard_decode_csd(struct SDCardContext* ctx) {
	uint32_t r[SD_CMD_RESPONSE_SIZE/4];
	uint32_t size_blk;
	int i;
	for (i = 0 ; i < SD_CMD_RESPONSE_SIZE/4 ; i++) /* volatile, unlike csr_rd_buf_uint32 */
		r[i] = __builtin_bswap32(*(volatile uint32_t*)(ctx->sc + CSR_SDCORE_CMD_RESPONSE_ADDR + 4*i));

	switch (r[0] >> 30) { /* CSD_STRUCTURE */
	case 0: { /* CSD 1.0, SDSC: (C_SIZE+1) * 2^(C_SIZE_MULT+2) * 2^READ_BL_LEN bytes */
		uint32_t c_size = ((r[1] & 0x3ff) << 2) | (r[2] >> 30);  /* [73:62] */
		uint32_t c_size_mult = (r[2] >> 15) & 0x7;                /* [49:47] */
		uint32_t read_bl_len = (r[1] >> 16) & 0xf;                /* [83:80] */
		if (read_bl_len < 9 || read_bl_len > 11)
			return 0;
		size_blk = (c_size + 1) << (c_size_mult + 2 + read_bl_len - 9);
		break;
	}
	case 1: { /* CSD 2.0, SDHC/SDXC: (C_SIZE+1) * 512 KiB */
		uint32_t c_size = ((r[1] & 0x3f) << 16) | (r[2] >> 16);   /* [69:48] */
		if ((c_size + 1) >= 4096) /* >= 2 GiB, also avoids the overflow */
			size_blk = 4194304;
		else
			size_blk = (c_size + 1) * 1024;
		break;
	}
	default:
		return 0;
	}

	/* 2 GiB - 512 B max: ioPosOffset is signed */
	if (size_blk >= 4194304)
		size_blk = 4194303;

	ctx->size_blk = size_blk;
	return 1;
}

/*-----------------------------------------------------------------------*/
/* SDCard user functions                                                 */
/*-----------------------------------------------------------------------*/
static int sdcard_init(struct SDCardContext* ctx) {
	uint32_t sc = ctx->sc;
	uint32_t ocr = 0;
	int timeout;
	int v2 = 1;
	int res;

	/* known state: no DMA */
	sdblock2mem_dma_enable_write(sc, 0);
	sdmem2block_dma_enable_write(sc, 0);

	/* Set SD clk freq to Initialization frequency, until the card is identified */
	sdcard_set_divider(ctx, 256); /* 390 kHz */
	busy_wait(1);

	for (timeout=1000; timeout>0; timeout--) {
		/* Set SDCard in SPI Mode (generate 80 dummy clocks) */
		sdphy_init_initialize_write(sc, 1);
		busy_wait(1);

		/* Set SDCard in Idle state */
		res = sdcard_go_idle(ctx);
		if (res == SD_OK)
			break;
		if (res == SD_HWHANG)
			return 0;
		busy_wait(1);
	}
	if (timeout == 0)
		return 0;

	/* CMD8: only answered by version 2.00+ cards, which must echo the argument */
	res = sdcard_send_if_cond(ctx);
	if (res == SD_HWHANG)
		return 0;
	if (res != SD_OK)
		v2 = 0; /* version 1.x card, standard capacity only */
	else if ((sdcard_response32(ctx) & 0xfff) != 0x1aa)
		return 0; /* voltage not supported / bad echo */
	ctx->v2 = v2;

	/* ACMD41 until the card reports power-up complete (OCR bit 31), up to ~1 s */
	/* Every unanswered command costs the 1 s hardware command timeout, so give up as
	   soon as it's clear there's no (SD) card: a card always answers CMD55. With no
	   card, Open fails after ~2 s (CMD8 + one CMD55) instead of looping for an hour. */
	{
		int acmd41_noanswer = 0;
	for (timeout=2000; timeout>0; timeout--) {
		res = sdcard_app_cmd(ctx, 0);
		if (res != SD_OK)
			return 0; /* no card, or SD_HWHANG */
		res = sdcard_app_send_op_cond(ctx, v2);
		if (res == SD_HWHANG)
			return 0;
		if (res != SD_OK) {
			if (++acmd41_noanswer >= 3)
				return 0; /* not an SD card (e.g. MMC) */
		} else {
			ocr = sdcard_response32(ctx);
			if (ocr & 0x80000000)
				break;
		}
		busy_wait(1);
	}
	}
	if (timeout == 0)
		return 0;
	/* CCS: block addressing (SDHC/SDXC) rather than byte addressing (SDSC) */
	ctx->hc = (v2 && (ocr & 0x40000000)) ? 1 : 0;

	/* Send identification */
	if (sdcard_all_send_cid(ctx) != SD_OK)
		return 0;

	/* Set Relative Card Address (RCA) */
	if (sdcard_set_relative_address(ctx) != SD_OK)
		return 0;
	ctx->rca = (sdcard_response32(ctx) >> 16) & 0xffff;

	/* identification done, Set SD clk freq to Operational frequency */
	/* (the busy_wait covers the trailing clocks of CMD3's response, at the old clock) */
	sdcard_set_divider(ctx, SDCARD_CLK_DIVIDER);
	busy_wait(1);

	/* Get CSD */
	if (sdcard_send_csd(ctx, ctx->rca) != SD_OK)
		return 0;
	if (!sdcard_decode_csd(ctx))
		return 0;

	/* Select card */
	if (sdcard_select_card(ctx, ctx->rca) != SD_OK)
		return 0;

	/* Set bus width */
	if (sdcard_app_cmd(ctx, ctx->rca) != SD_OK)
		return 0;
	if (sdcard_app_set_bus_width(ctx) != SD_OK)
		return 0;

	/* Speed mode. The LiteX BIOS switches to High Speed, but the LiteX PHY samples the data
	   lines a fixed few ns after the SD clock rising edge, which is exactly when a High Speed
	   card changes its outputs: some cards then give sporadic bit errors (measured: DAT2 1->0,
	   at any clock from 6.25 to 25 MHz). In default speed the card changes its outputs after
	   the falling edge, half a period earlier: no errors, and 25 MHz is the default speed max.
	   (Re-selecting default speed explicitly also records the card's answer in hs_status.)
	   Not fatal either way: the card powers up in default speed. */
#ifdef SDCARD_USE_HIGH_SPEED
	if (sdcard_set_speed(ctx, 1) == SD_HWHANG)
		return 0;
#else
	if (sdcard_set_speed(ctx, 0) == SD_HWHANG)
		return 0;
#endif

	/* Set block length (only matters for SDSC) */
	if (sdcard_set_blocklen(ctx, 512) != SD_OK)
		return 0;

	return 1;
}

/*-----------------------------------------------------------------------*/
/* SDCard data transfers                                                 */
/*-----------------------------------------------------------------------*/

/* wait for the card to be back in 'tran' state, returning its R1 status in *r1 */
__attribute__ ((section (".text.sddriver"))) static int sdcard_wait_tran(struct SDCardContext *ctx, uint32_t *r1) {
	unsigned long i;
	unsigned long start = TickCount();
	int noanswer = 0;
	int res = SD_TIMEOUT;
	/* each CMD13 is several NuBus accesses (>= 1 us), so the iteration cap is > 1 s too */
	for (i = 0 ; i < (SD_TICKS_TRAN << 16) ; i++) {
		res = sdcard_send_status(ctx);
		if (res == SD_HWHANG)
			return res;
		if (res != SD_OK) {
			/* each unanswered command costs the 1 s hardware timeout */
			if (++noanswer >= 3)
				return res;
		} else {
			*r1 = sdcard_response32(ctx);
			if (SD_R1_STATE(*r1) == SD_R1_STATE_TRAN)
				return SD_OK;
			res = SD_TIMEOUT;
		}
		if (SD_TICKS_EXPIRED(i, start, SD_TICKS_TRAN))
			break;
	}
	return res;
}

/* after a failure, try to bring the card back to 'tran' state */
__attribute__ ((section (".text.sddriver"))) static void sdcard_recover(struct SDCardContext *ctx) {
	uint32_t r1;
	int res = sdcard_send_status(ctx);
	if (res == SD_HWHANG)
		return;
	if (res == SD_OK) {
		r1 = sdcard_response32(ctx);
		switch (SD_R1_STATE(r1)) {
		case SD_R1_STATE_TRAN:
			return;
		case 5: /* data */
		case 6: /* rcv */
			sdcard_stop_transmission(ctx);
			break;
		default: /* prg, ... */
			break;
		}
	} else {
		/* no answer, unknown state: try to stop whatever is going on */
		sdcard_stop_transmission(ctx);
	}
	sdcard_wait_tran(ctx, &r1);
}

__attribute__ ((section (".text.sddriver"))) static int sdcard_read_once(struct SDCardContext *ctx, uint32_t block, uint32_t n) {
	uint32_t sc = ctx->sc;
	uint32_t addr = ctx->hc ? block : (block << 9);
	unsigned long i;
	int res;

	/* with enable == 0 the DMA drops whatever was left in its FIFO; give it time to drain */
	sdblock2mem_dma_enable_write(sc, 0);
	(void)sdblock2mem_dma_enable_read(sc); /* ordered after the write: the DMA is disabled from now on */
	delay(50);

	sdblock2mem_dma_base_write(sc, SDCARD_BUF_DMA_ADDR);
	sdblock2mem_dma_length_write(sc, 512*n);
	sdblock2mem_dma_enable_write(sc, 1);

	sdcore_block_length_write(sc, 512);
	sdcore_block_count_write(sc, n);
	res = sdcard_send_command(ctx, addr, (n > 1) ? 18 : 17,
				  (SDCARD_CTRL_DATA_TRANSFER_READ << 5) | SDCARD_CTRL_RESPONSE_SHORT,
				  SD_TICKS_CMD + (n << SD_TICKS_PER_BLK_SHIFT));
	if (res == SD_HWHANG)
		return res;
	if (res != SD_OK)
		goto fail;
	if (sdcard_response32(ctx) & SD_R1_ERRORS) {
		res = SD_CARDERROR;
		goto fail;
	}
	if (sdcore_data_event_read(sc) & 0x4) {
		res = SD_TIMEOUT;
		goto fail;
	}
	/* NB: the gateware doesn't check the data CRC, corrupted data can't be detected */

	/* Wait for DMA Writer to complete (all words written to the buffer) */
	for (i = 0 ; i < SD_POLL_DMA ; i++) {
		if (sdblock2mem_dma_done_read(sc) & 0x1)
			break;
	}
	if (i == SD_POLL_DMA) {
		res = SD_TIMEOUT;
		goto fail;
	}

	/* Stop transmission (Only for multiple block reads, no CMD23) */
	if (n > 1) {
		res = sdcard_stop_transmission(ctx);
		if (res == SD_HWHANG)
			return res;
		if (res != SD_OK)
			goto fail;
	}

	sdblock2mem_dma_enable_write(sc, 0);
	return SD_OK;

 fail:
	sdblock2mem_dma_enable_write(sc, 0);
	sdcard_recover(ctx);
	return res;
}

int sdcard_read(struct SDCardContext *ctx, uint32_t block, uint32_t count, uint8_t* buf) {
	uint8_t *sd_buf = (uint8_t*)(ctx->sc + SDCARD_BUF_OFFSET);
	int res = SD_OK;

	if (ctx->dead)
		return SD_HWHANG;

	while (count) {
		uint32_t nblocks;
		int try;
#ifdef SDCARD_CMD18_SUPPORT
		nblocks = min(count, SDCARD_MAX_BLK_PER_OP);
#else
		nblocks = 1;
#endif

		for (try = 0 ; try < SD_RETRIES ; try++) {
			if (try)
				ctx->read_retries++;
			res = sdcard_read_once(ctx, block, nblocks);
			if ((res == SD_OK) || (res == SD_HWHANG))
				break;
		}
		if (res != SD_OK)
			return res;

		BlockMoveData(sd_buf, buf, 512*nblocks);

		/* Update Block/Buffer/Count */
		block += nblocks;
		buf += 512*nblocks;
		count -= nblocks;
	}

	return SD_OK;
}

/* ACMD22: number of blocks written without error by the last write */
__attribute__ ((section (".text.sddriver"))) static int sdcard_app_send_num_wr_blocks(struct SDCardContext *ctx, uint32_t *nwr) {
	uint32_t sc = ctx->sc;
	unsigned long i;
	int res;

	sdblock2mem_dma_enable_write(sc, 0);
	(void)sdblock2mem_dma_enable_read(sc); /* ordered after the write: the DMA is disabled from now on */
	delay(50);
	sdblock2mem_dma_base_write(sc, SDCARD_BUF_DMA_ADDR);
	sdblock2mem_dma_length_write(sc, 4);
	sdblock2mem_dma_enable_write(sc, 1);

	res = sdcard_app_cmd(ctx, ctx->rca);
	if (res != SD_OK)
		goto done;
	sdcore_block_length_write(sc, 4);
	sdcore_block_count_write(sc, 1);
	res = sdcard_send_command(ctx, 0, 22,
				  (SDCARD_CTRL_DATA_TRANSFER_READ << 5) | SDCARD_CTRL_RESPONSE_SHORT,
				  SD_TICKS_CMD + (1ul << SD_TICKS_PER_BLK_SHIFT));
	if (res != SD_OK)
		goto done;
	if (sdcore_data_event_read(sc) & 0x4) {
		res = SD_TIMEOUT;
		goto done;
	}
	for (i = 0 ; i < SD_POLL_DMA ; i++) {
		if (sdblock2mem_dma_done_read(sc) & 0x1)
			break;
	}
	if (i == SD_POLL_DMA) {
		res = SD_TIMEOUT;
		goto done;
	}
	/* big-endian on the wire, stored in order: reads as-is on the 68k */
	*nwr = *(volatile uint32_t*)(sc + SDCARD_BUF_OFFSET);

 done:
	sdblock2mem_dma_enable_write(sc, 0);
	return res;
}

__attribute__ ((section (".text.sddriver"))) static int sdcard_write_once(struct SDCardContext *ctx, uint32_t block, uint32_t n, uint8_t* buf) {
	uint32_t sc = ctx->sc;
	uint32_t addr = ctx->hc ? block : (block << 9);
	uint32_t r1, nwr;
	int res;

	/* posted writes stay in order, so the data is in the buffer before the DMA starts */
	BlockMoveData(buf, (void*)(sc + SDCARD_BUF_OFFSET), 512*n);

	sdmem2block_dma_enable_write(sc, 0);
	sdmem2block_dma_base_write(sc, SDCARD_BUF_DMA_ADDR);
	sdmem2block_dma_length_write(sc, 512*n);
	sdmem2block_dma_enable_write(sc, 1);

	sdcore_block_length_write(sc, 512);
	sdcore_block_count_write(sc, n);
	res = sdcard_send_command(ctx, addr, (n > 1) ? 25 : 24,
				  (SDCARD_CTRL_DATA_TRANSFER_WRITE << 5) | SDCARD_CTRL_RESPONSE_SHORT,
				  SD_TICKS_CMD + (n << SD_TICKS_PER_BLK_SHIFT));
	if (res == SD_HWHANG)
		return res;
	if (res != SD_OK) {
		/* No response, so the SD core never consumed the data, but the DMA has
		   already pre-filled its FIFO. The gateware doesn't flush that FIFO, so
		   any later write would start with these stale bytes: refuse writes. */
		ctx->wr_broken = 1;
		sdmem2block_dma_enable_write(sc, 0);
		sdcard_recover(ctx);
		return res;
	}
	if (sdcard_response32(ctx) & SD_R1_ERRORS) {
		res = SD_CARDERROR;
		goto fail;
	}
	/* NB: sdphy_dataw_status (CRC status token) is cleared as soon as the PHY is back
	   to idle, before we can read it; ACMD22 below is used instead */

	/* Stop transmission (Only for multiple block writes, no CMD23) */
	if (n > 1) {
		res = sdcard_stop_transmission(ctx);
		if (res == SD_HWHANG)
			return res;
		if (res != SD_OK)
			goto fail;
	}

	/* wait for programming to finish, and check the status */
	res = sdcard_wait_tran(ctx, &r1);
	if (res == SD_HWHANG)
		return res;
	if (res != SD_OK)
		goto fail;
	if (r1 & SD_R1_ERRORS) {
		res = SD_CARDERROR;
		goto fail;
	}

	/* the CRC status tokens aren't visible, so ask the card how many blocks made it */
	res = sdcard_app_send_num_wr_blocks(ctx, &nwr);
	if (res == SD_HWHANG)
		return res;
	if (res != SD_OK)
		goto fail;
	if (nwr != n) {
		res = SD_WRITEERROR;
		goto fail;
	}

	sdmem2block_dma_enable_write(sc, 0);
	return SD_OK;

 fail:
	sdmem2block_dma_enable_write(sc, 0);
	sdcard_recover(ctx);
	return res;
}

int sdcard_write(struct SDCardContext *ctx, uint32_t block, uint32_t count, uint8_t* buf) {
	int res = SD_OK;

	if (ctx->dead)
		return SD_HWHANG;

	while (count) {
		uint32_t nblocks;
		int try;
#ifdef SDCARD_CMD25_SUPPORT
		nblocks = min(count, SDCARD_MAX_BLK_PER_OP);
#else
		nblocks = 1;
#endif

		/* retrying is only safe while the write FIFO is known to be empty */
		for (try = 0 ; try < SD_RETRIES ; try++) {
			if (ctx->wr_broken)
				return SD_WRITEERROR;
			if (try)
				ctx->write_retries++;
			res = sdcard_write_once(ctx, block, nblocks, buf);
			if ((res == SD_OK) || (res == SD_HWHANG))
				break;
		}
		if (res != SD_OK)
			return res;

		/* Update Block/Buffer/Count */
		block += nblocks;
		buf += 512*nblocks;
		count -= nblocks;
	}

	return SD_OK;
}

#endif /* ENABLE_SDCARD */
