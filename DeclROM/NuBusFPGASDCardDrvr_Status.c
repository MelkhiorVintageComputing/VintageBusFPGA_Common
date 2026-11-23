#if defined(ENABLE_SDCARD)

#include "NuBusFPGASDCardDrvr.h"

#pragma parameter __D0 cNuBusFPGASDCardStatus(__A0, __A1)
OSErr cNuBusFPGASDCardStatus(CntrlParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce)
{
	OSErr ret = noErr;
	struct SDCardContext *ctx = NULL;
	
	if (dce->dCtlStorage)
		ctx = *(struct SDCardContext**)dce->dCtlStorage;

	if (ctx) {
		switch (pb->csCode)
			{
			case drvStsCode: /* DriveStatus, IM II-215 */
				BlockMoveData(&ctx->drvsts, pb->csParam, sizeof(DrvSts));
				ret = noErr;
				break;
			case kSDCardInfo: {
				struct SDCardInfo info;
				info.version = 1;
				info.flags = (ctx->hc ? 1 : 0) | (ctx->v2 ? 2 : 0) | (ctx->dead ? 4 : 0) | (ctx->wr_broken ? 8 : 0);
				info.hs_status = ctx->hs_status;
				info.divider = ctx->divider;
				info.read_retries = ctx->read_retries;
				info.write_retries = ctx->write_retries;
				info.size_blk = ctx->size_blk;
				BlockMoveData(&info, pb->csParam, sizeof(info));
				ret = noErr;
				break;
			}
			default:
				ret = statusErr;
				break;
			}
	} else {
		ret = offLinErr; /* r/w requested for an off-line drive */
	}

	if (!(pb->ioTrap & (1<<noQueueBit)))
		IODone((DCtlPtr)dce, ret);
	return ret;
}

#endif /* ENABLE_SDCARD */
