#if defined(ENABLE_SDCARD)

#include "NuBusFPGASDCardDrvr.h"

#if 0
OSErr changeSDCardIRQ(AuxDCEPtr dce, char en, OSErr err) {
	struct SDCardContext *ctx = *(struct SDCardContext**)dce->dCtlStorage;
	
   if (en != ctx->irqen) {
	   /* write_reg(dce, GOBOFB_DEBUG, 0xBEEF0005); */
	   /* write_reg(dce, GOBOFB_DEBUG, en); */
	   
	   if (en) {
	   	   if (SIntInstall(ctx->siqel, dce->dCtlSlot)) {
	   		   return err;
	   	   }
	   } else {
	   	   if (SIntRemove(ctx->siqel, dce->dCtlSlot)) {
	   		   return err;
	   	   }
	   }

	   write_reg(dce, DMA_IRQ_CTL, en ? revb(0x3) : revb(0x2)); // 0x2: always clear pending interrupt
	   ctx->irqen = en;
   }
   return noErr;
}
#endif


#pragma parameter __D0 cNuBusFPGASDCardCtl(__A0, __A1)
OSErr cNuBusFPGASDCardCtl(CntrlParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce)
{
	OSErr ret = noErr;
	struct SDCardContext *ctx = NULL;
	
	if (dce->dCtlStorage)
		ctx = *(struct SDCardContext**)dce->dCtlStorage;
	
	if (ctx) {
		switch (pb->csCode)
			{
			case killCode: /* everything is synchronous, nothing to kill */
				ret = noErr;
				break;
			case kVerify: /* nothing to verify */
			case kFormat: /* nothing to format */
				ret = noErr;
				break;
			case kDriveInfo: /* IM V-470 */
				/* unspecified drive type (1), external (bit 8), fixed (bit 10) */
				pb->csParam[0] = 0x0000;
				pb->csParam[1] = 0x0501;
				ret = noErr;
				break;
			case kSDCardSetClock: {
				uint32_t d = ((uint32_t)(uint16_t)pb->csParam[0] << 16) | (uint16_t)pb->csParam[1];
				if ((d < 2) || (d > 256) || (d & (d - 1))) {
					ret = paramErr;
				} else {
					sdcard_set_divider(ctx, d);
					ret = noErr;
				}
				break;
			}
			case kSDCardSetSpeed: {
				uint32_t m = ((uint32_t)(uint16_t)pb->csParam[0] << 16) | (uint16_t)pb->csParam[1];
				if (m > 1)
					ret = paramErr;
				else
					ret = (sdcard_set_speed(ctx, m) == SD_OK) ? noErr : ioErr;
				break;
			}
			default:
				ret = controlErr;
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
