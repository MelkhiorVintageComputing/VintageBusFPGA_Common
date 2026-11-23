#if defined(ENABLE_SDCARD)

#include "NuBusFPGASDCardDrvr.h"

/* #include <DriverServices.h> */

inline void waitSome(unsigned long bound) {
  unsigned long i;
  for (i = 0 ; i < bound ; i++) {
    asm volatile("nop");
  }
}

/* NuBusFPGA only supports 32-bits mode, so no MMU mode switching here */
__attribute__ ((section (".text.sddriver"))) static OSErr doSync(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce, struct SDCardContext *ctx) {
	OSErr ret = noErr;
	unsigned long abs_offset = 0;
	unsigned long blk, cnt;
	int is_read;

	pb->ioActCount = 0;

	/* IOParamPtr: Devices 1-53 (p73) */
	/* **** WHERE **** */
	switch(pb->ioPosMode & 0x000F) { // ignore rdVerify
	case fsAtMark:
		abs_offset = dce->dCtlPosition;
		break;
	case fsFromStart:
		abs_offset = pb->ioPosOffset;
		break;
	case fsFromMark:
		abs_offset = dce->dCtlPosition + pb->ioPosOffset;
		break;
	default: /* e.g. fsFromLEOF, meaningless for a disk */
		return paramErr;
	}

	/* **** WHAT **** */
	/* Devices 1-33 (p53) */
	if ((pb->ioTrap & 0x00FF) == aRdCmd) {
		is_read = 1;
	} else if ((pb->ioTrap & 0x00FF) == aWrCmd) {
		is_read = 0;
	} else {
		return paramErr;
	}

	if ((abs_offset & 0x01FF) || (pb->ioReqCount & 0x01FF))
		return paramErr;
	blk = abs_offset >> 9;
	cnt = pb->ioReqCount >> 9;
	if ((blk > ctx->size_blk) || (cnt > (ctx->size_blk - blk)))
		return paramErr;

	if (is_read) {
		if (!(pb->ioPosMode & rdVerify)) { // rdVerify, let's ignore it for now
			if (sdcard_read(ctx, blk, cnt, (uint8_t*)pb->ioBuffer)) {
				ret = readErr;
				goto done;
			}
		}
	} else {
		if (sdcard_write(ctx, blk, cnt, (uint8_t*)pb->ioBuffer)) {
			ret = writErr;
			goto done;
		}
	}
	pb->ioActCount = pb->ioReqCount;
	dce->dCtlPosition = abs_offset + pb->ioReqCount;
	pb->ioPosOffset = dce->dCtlPosition;

 done:
	return ret;
}

/* Devices 1-34 (p54) */
#pragma parameter __D0 cNuBusFPGASDCardPrime(__A0, __A1)
OSErr cNuBusFPGASDCardPrime(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce) {
	OSErr ret = noErr;
	struct SDCardContext *ctx = NULL;

	if (dce->dCtlStorage)
		ctx = *(struct SDCardContext**)dce->dCtlStorage;

	if (ctx) {
		ret = doSync(pb, dce, ctx);
	} else {
		ret = offLinErr;  /* r/w requested for an off-line drive */
	}

	if (!(pb->ioTrap & (1<<noQueueBit)))
		IODone((DCtlPtr)dce, ret);
	return ret;
}


#endif /* ENABLE_SDCARD */
