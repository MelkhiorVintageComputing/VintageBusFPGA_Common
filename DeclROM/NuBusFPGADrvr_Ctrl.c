#include "NuBusFPGADrvr.h"

void linearGamma(NuBusFPGADriverGlobalsPtr dStore) {
	int i;
	dStore->gamma.gVersion = 0;
	dStore->gamma.gType = 0;
	dStore->gamma.gFormulaSize = 0;
	dStore->gamma.gChanCnt = 3;
	dStore->gamma.gDataCnt = 256;
	dStore->gamma.gDataWidth = 8;
	for (i = 0 ; i < 256 ; i++) {
		dStore->gamma.gFormulaData[0][i] = i;
		dStore->gamma.gFormulaData[1][i] = i;
		dStore->gamma.gFormulaData[2][i] = i;
	}
}

OSErr changeIRQ(AuxDCEPtr dce, char en, OSErr err) {
   NuBusFPGADriverGlobalsHdl dStoreHdl = (NuBusFPGADriverGlobalsHdl)dce->dCtlStorage;
   NuBusFPGADriverGlobalsPtr dStore = *dStoreHdl;
   char busMode = 1;
   if (en != dStore->irqen) {
	   /* write_reg(dce, GOBOFB_DEBUG, 0xBEEF0005); */
	   /* write_reg(dce, GOBOFB_DEBUG, en); */
	   
	   if (en) {
	   	   if (SIntInstall(dStore->siqel, dce->dCtlSlot)) {
	   		   return err;
	   	   }
		   /* write_reg(dce, GOBOFB_DEBUG, 0x88888888); */
		   /* write_reg(dce, GOBOFB_DEBUG, dStore->siqel); */
		   /* write_reg(dce, GOBOFB_DEBUG, dStore->siqel->sqLink); */
	   } else {
	   	   if (SIntRemove(dStore->siqel, dce->dCtlSlot)) {
	   		   return err;
	   	   }
	   }

	   SwapMMUMode ( &busMode );
	   write_reg(dce, GOBOFB_VBL_MASK, en ? GOBOFB_INTR_VBL : 0);
	   SwapMMUMode ( &busMode );
	   dStore->irqen = en;
   }
   return noErr;
}

/*
  7.1.1:
     11 Debug: 0x00000003
      2 Debug: 0x00000004
      1 Debug: 0x00000005
      4 Debug: 0x00000006
      1 �Debug: 0x00000002

  7.5.3:
      4 Debug: 0x00000002
     12 Debug: 0x00000003
      3 Debug: 0x00000004
      5 Debug: 0x00000005
      5 Debug: 0x00000006
      5 Debug: 0x00000009
      4 Debug: 0x0000000a
      5 Debug: 0x00000010
      1 �Debug: 0x00000002

  8.1:
      5 Debug: 0x00000002
      9 Debug: 0x00000003
      1 Debug: 0x00000004
      6 Debug: 0x00000005
      6 Debug: 0x00000006
      4 Debug: 0x00000009
      5 Debug: 0x0000000a
      4 Debug: 0x00000010
      1 �Debug: 0x00000002
*/

#pragma parameter __D0 cNuBusFPGACtl(__A0, __A1)
OSErr cNuBusFPGACtl(CntrlParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce)
{
   NuBusFPGADriverGlobalsHdl dStoreHdl = (NuBusFPGADriverGlobalsHdl)dce->dCtlStorage;
   NuBusFPGADriverGlobalsPtr dStore = *dStoreHdl;
   
   short ret = -1;
   char	busMode = 1;

   /* write_reg(dce, GOBOFB_DEBUG, 0xBEEF0001); */
   /* write_reg(dce, GOBOFB_DEBUG, pb->csCode); */

  switch (pb->csCode)
  {
  case -1:
	  asm volatile(".word 0xfe16\n");
  	  break;
  case cscReset: /* 0x0 */
	   {
		   VDPageInfo	*vPInfo = (VDPageInfo *)*(long *)pb->csParam;
		   dStore->curMode = nativeVidMode;
		   dStore->curDepth = kDepthMode1; /* 8-bit */
		   vPInfo->csMode = nativeVidMode;
		   vPInfo->csPage = 0;
		   vPInfo->csBaseAddr = 0;
		   ret = noErr;
	   }
  	  break;
  case cscKillIO: /* 0x1 */
	  asm volatile(".word 0xfe16\n");
	  ret = noErr;
	  break;
  case cscSetMode: /* 0x2 */
	   {
		   VDPageInfo	*vPInfo = (VDPageInfo *)*(long *)pb->csParam;

		   ret = reconfHW(dce, dStore->curMode, vPInfo->csMode, vPInfo->csPage);
   
		  if (ret == noErr)
			  vPInfo->csBaseAddr = (void*)(vPInfo->csPage * 1024 * 1024 * 4);
	   }
	  break;
  case cscSetEntries: /* 0x3 */
	  if (1) {
		  VDSetEntryRecord	**vdentry = (VDSetEntryRecord **)(long *)pb->csParam;
		  int csCount = (*vdentry)->csCount;
		  int csStart = (*vdentry)->csStart;
		  int i;
		  if (csCount <= 0) {
			  ret = noErr;
			  goto cscSetMode_done;
		  }
		  SwapMMUMode ( &busMode );
		  if (csStart < 0) {
			  for (i = 0 ; i <= csCount ; i++) {
				  unsigned short idx = ((*vdentry)->csTable[i].value & 0x0FF);
				  /* dStore->shadowClut[idx*3+0] = (*vdentry)->csTable[i].rgb.red; */
				  /* dStore->shadowClut[idx*3+1] = (*vdentry)->csTable[i].rgb.green; */
				  /* dStore->shadowClut[idx*3+2] = (*vdentry)->csTable[i].rgb.blue; */
				  
				  write_reg(dce, GOBOFB_LUT_ADDR, (idx & 0xFF));
				  write_reg(dce, GOBOFB_LUT, dStore->gamma.gFormulaData[0][(*vdentry)->csTable[i].rgb.red>>8 & 0xFF]);
				  write_reg(dce, GOBOFB_LUT, dStore->gamma.gFormulaData[1][(*vdentry)->csTable[i].rgb.green>>8 & 0xFF]);
				  write_reg(dce, GOBOFB_LUT, dStore->gamma.gFormulaData[2][(*vdentry)->csTable[i].rgb.blue>>8 & 0xFF]);
				  /* write_reg(dce, GOBOFB_LUT, (*vdentry)->csTable[i].rgb.red); */
				  /* write_reg(dce, GOBOFB_LUT, (*vdentry)->csTable[i].rgb.green); */
				  /* write_reg(dce, GOBOFB_LUT, (*vdentry)->csTable[i].rgb.blue); */
			  }
		  } else {
			  write_reg(dce, GOBOFB_LUT_ADDR, (csStart & 0xFF));
			  for (i = 0 ; i <= csCount ; i++) {
				  /* dStore->shadowClut[(i+csStart)*3+0] = (*vdentry)->csTable[i].rgb.red; */
				  /* dStore->shadowClut[(i+csStart)*3+1] = (*vdentry)->csTable[i].rgb.green; */
				  /* dStore->shadowClut[(i+csStart)*3+2] = (*vdentry)->csTable[i].rgb.blue; */
				  
				  write_reg(dce, GOBOFB_LUT, dStore->gamma.gFormulaData[0][(*vdentry)->csTable[i].rgb.red>>8 & 0xFF]);
				  write_reg(dce, GOBOFB_LUT, dStore->gamma.gFormulaData[1][(*vdentry)->csTable[i].rgb.green>>8 & 0xFF]);
				  write_reg(dce, GOBOFB_LUT, dStore->gamma.gFormulaData[2][(*vdentry)->csTable[i].rgb.blue>>8 & 0xFF]);
				  /* write_reg(dce, GOBOFB_LUT, (*vdentry)->csTable[i].rgb.red); */
				  /* write_reg(dce, GOBOFB_LUT, (*vdentry)->csTable[i].rgb.green); */
				  /* write_reg(dce, GOBOFB_LUT, (*vdentry)->csTable[i].rgb.blue); */
			  }
		  }
		  SwapMMUMode ( &busMode );
		  ret = noErr;
	  } else {
			   ret = noErr;
	  }
	  cscSetMode_done:
	  break;
  case cscSetGamma: /* 0x4 */
	  {
		   VDGammaRecord	*vdgamma = (VDGammaRecord *)*(long *)pb->csParam;
		   GammaTbl	*gammaTbl = (GammaTbl*)vdgamma->csGTable;
		   int i;
		   if (gammaTbl == NULL) {
			   linearGamma(dStore);
		   } else {
			   ret = noErr;
			   if (gammaTbl->gDataWidth != 8)
				   ret = paramErr;
			   if (gammaTbl->gDataCnt != 256) // 8-bits
				   ret = paramErr;
			   if ((gammaTbl->gChanCnt != 1) && (gammaTbl->gChanCnt != 3))
				   ret = paramErr;
			   if ((gammaTbl->gType != 0) && (gammaTbl->gType != 0xFFFFBEEF))
				   ret = paramErr;
			   if (gammaTbl->gFormulaSize != 0)
				   ret = paramErr;
			   if (ret != noErr)
				   goto done;
			   
			   dStore->gamma.gVersion =     gammaTbl->gVersion;
			   dStore->gamma.gType =        gammaTbl->gType;
			   dStore->gamma.gFormulaSize = gammaTbl->gFormulaSize;
			   dStore->gamma.gChanCnt =     gammaTbl->gChanCnt;
			   dStore->gamma.gDataCnt =     gammaTbl->gDataCnt;
			   dStore->gamma.gDataWidth =   gammaTbl->gDataWidth;
			   
			   int og, ob;
			   if (gammaTbl->gChanCnt == 1)
				   og = ob = 0;
			   else {
				   og = 256;
				   ob = 512;
			   }
			   for (i = 0 ; i < gammaTbl->gDataCnt ; i++) {
				   dStore->gamma.gFormulaData[0][i] = ((unsigned char*)gammaTbl->gFormulaData)[i +  0];
				   dStore->gamma.gFormulaData[1][i] = ((unsigned char*)gammaTbl->gFormulaData)[i + og];
				   dStore->gamma.gFormulaData[2][i] = ((unsigned char*)gammaTbl->gFormulaData)[i + ob];
			   }
		   }
 		   ret = noErr;
	   }
	  break;
  case cscGrayPage: /* 0x5 == cscGrayScreen */
	   {
		   VDPageInfo	*vPInfo = (VDPageInfo *)*(long *)pb->csParam;
		   const uint8_t idx = dStore->curMode % 4; // checkme
		   UInt32 a32 = dce->dCtlDevBase;
		   UInt32 a32_l0, a32_l1;
		   UInt32 a32_4p0, a32_4p1;
		   const uint32_t wb = dStore->hres[0] >> idx;
		   unsigned short j, i;
		   short npage = (vPInfo->csMode == kDepthMode5) ? 1 : 2;
		   if (vPInfo->csPage >= npage) {
			   return paramErr;
			   goto done;
		   }

		   a32 += vPInfo->csPage * 1024 * 1024 * 4; /* fixme */
		   
		   SwapMMUMode ( &busMode );
#if 0
		   if ((dStore->curMode != kDepthMode5) && (dStore->curMode != kDepthMode6)) {
			   /* grey the screen */
			   a32_l0 = a32;
			   a32_l1 = a32 + wb;
			   for (j = 0 ; j < dStore->vres[0] ; j+= 2) {
				   a32_4p0 = a32_l0;
				   a32_4p1 = a32_l1;
				   for (i = 0 ; i < wb ; i += 4) {
					   *((UInt32*)a32_4p0) = 0xFF00FF00;
					   *((UInt32*)a32_4p1) = 0x00FF00FF;
					   a32_4p0 += 4;
					   a32_4p1 += 4;
				   }
				   a32_l0 += 2*wb;
				   a32_l1 += 2*wb;
			   }
		   } else {
			   /* testing */
			   a32_l0 = a32;
			   a32_l1 = a32 + dStore->hres[0]*4;
			   for (j = 0 ; j < dStore->vres[0] ; j+= 2) {
				   a32_4p0 = a32_l0;
				   a32_4p1 = a32_l1;
				   for (i = 0 ; i < dStore->hres[0] ; i ++ ) {
					   *((UInt32*)a32_4p0) = (i&0xFF);//(i&0xFF) | (i&0xFF)<<8 | (i&0xff)<<24;
					   *((UInt32*)a32_4p1) = (i&0xFF)<<16;//(i&0xFF) | (i&0xFF)<<8 | (i&0xff)<<24;
					   a32_4p0 += 4;
					   a32_4p1 += 4;
				   }
				   a32_l0 += 2*dStore->hres[0]*4;
				   a32_l1 += 2*dStore->hres[0]*4;
			   }
		   }
#else

#define WAIT_FOR_HW_LE(accel_le)						\
	while (accel_le->reg_status & (1<<WORK_IN_PROGRESS_BIT))
		   
		   const UInt32 fgcolor = 0; // FIXME: per-depth?
		   struct goblin_accel_regs* accel_le = (struct goblin_accel_regs*)(dce->dCtlDevBase+GOBOFB_ACCEL_LE);
		   WAIT_FOR_HW_LE(accel_le);
		   accel_le->reg_width = dStore->hres[dStore->curMode - nativeVidMode]; // pixels
		   accel_le->reg_height = dStore->vres[dStore->curMode - nativeVidMode];
		   accel_le->reg_bitblt_dst_x = 0; // pixels
		   accel_le->reg_bitblt_dst_y = 0;
		   accel_le->reg_dst_ptr = 0;
		   accel_le->reg_fgcolor = fgcolor;
		   accel_le->reg_cmd = (1<<DO_FILL_BIT);
		   WAIT_FOR_HW_LE(accel_le);

#undef WAIT_FOR_HW_LE
		   
#endif
		   SwapMMUMode ( &busMode );
		   
		   ret = noErr;
	   }
	  break;
  case cscSetGray: /* 0x6 */
	   {
		   VDGrayRecord	*vGInfo = (VDGrayRecord *)*(long *)pb->csParam;
		   dStore->gray = vGInfo->csMode;
		   ret = noErr;
	   }
	  break;
	  
  case cscSetInterrupt: /* 0x7 */
	   {
		   VDFlagRecord	*vdflag = (VDFlagRecord *)*(long *)pb->csParam;
		   ret = changeIRQ(dce, 1 - vdflag->csMode, controlErr);
	   }
  	  break;

  case cscDirectSetEntries: /* 0x8 */
	  asm volatile(".word 0xfe16\n");
	  ret = controlErr;
	  break;

  case cscSetDefaultMode: /* 0x9 */
	  {
		   VDDefMode	*vddefm = (VDDefMode *)*(long *)pb->csParam;

		   ret = updatePRAM(dce, vddefm->csID, dStore->curDepth, 0);
	  }
	  break;

  case cscSwitchMode: /* 0xa */
	  {
		  VDSwitchInfoRec	*vdswitch = *(VDSwitchInfoRec **)(long *)pb->csParam;

		  ret = reconfHW(dce, vdswitch->csData, vdswitch->csMode, vdswitch->csPage);
   
		  if (ret == noErr)
			  vdswitch->csBaseAddr = (void*)(vdswitch->csPage * 1024 * 1024 * 4);
	  }
	  break;

	  /* cscSetSync */ /* 0xb */
	  /* 0xc ... 0xf : undefined */

  case cscSavePreferredConfiguration: /* 0x10 */
	   {
		  VDSwitchInfoRec	*vdswitch = *(VDSwitchInfoRec **)(long *)pb->csParam;

		  ret = updatePRAM(dce, vdswitch->csData, vdswitch->csMode, 0);
	   }
	  break;

	  /* 0x11 .. 0x15 : undefined */

	  /* cscSetHardwareCursor */ /* 0x16 */
	  /* cscDrawHardwareCursor */ /* 0x17 */
	  /* cscSetConvolution */ /* 0x18 */
	  /* cscSetPowerState */ /* 0x19 */
	  /* cscPrivateControlCall */ /* 0x1a */
	  /* 0x1b : undefined */
	  /* cscSetMultiConnect */ /* 0x1c */
	  /* cscSetClutBehavior */ /* 0x1d */
	  /* 0x1e : undefined */
	  /* cscSetDetailedTiming */ /* 0x1f */
	  /* 0x20 : undefined */
	  /* cscDoCommunication */ /* 0x21 */ 
	  /* cscProbeConnection */ /* 0x22 */
	  
  default: /* always return controlErr for unknown csCode */
	  asm volatile(".word 0xfe16\n");
	  ret = controlErr;
	  break;
  }

 done:
  if (!(pb->ioTrap & (1<<noQueueBit)))
	  IODone((DCtlPtr)dce, ret);

  return ret;
}

#if defined(ENABLE_HDMI_ALT_CHANGE)
#if defined(NUBUSFPGA)
#include "../../nubusfpga_csr_goblin.h"
#include "../../nubusfpga_csr_crg.h"
#elif defined(IISIFPGA)
#include "../../iisifpga_csr_goblin.h"
#include "../../iisifpga_csr_crg.h"
#elif defined(LC32FPGA)
#include "../../lc32fpga_csr_goblin.h"
#include "../../lc32fpga_csr_crg.h"
#elif defined(QUADRAFPGA)
#include "../../quadrafpga_csr_crg.h"
#include "../../quadrafpga_csr_goblin.h"
#else
#error "no board defined"
#endif


		// access to the MMCM
#include "NuBusFPGADrvr_MMCM.h"

#endif

OSErr reconfHW(AuxDCEPtr dce, unsigned char mode, unsigned char depth, unsigned short page) {
	NuBusFPGADriverGlobalsHdl dStoreHdl = (NuBusFPGADriverGlobalsHdl)dce->dCtlStorage;
	NuBusFPGADriverGlobalsPtr dStore = *dStoreHdl;
	const short npage = (depth == kDepthMode5) ? 1 : 2;
	OSErr err = noErr;
	char busMode = 1;

	/* write_reg(dce, GOBOFB_DEBUG, 0xBEEF0031); */
	/* write_reg(dce, GOBOFB_DEBUG, mode); */
	/* write_reg(dce, GOBOFB_DEBUG, depth); */
	/* write_reg(dce, GOBOFB_DEBUG, page); */
	
	if ((mode == dStore->curMode) &&
		(depth == dStore->curDepth) &&
		(page == dStore->curPage)) {
		return noErr;
	}
		  
	if (page >= npage)
		return paramErr;

	if ((mode < nativeVidMode) ||
		(mode > dStore->maxMode))
		return paramErr;
		  
	switch (depth) {
	case kDepthMode1:
		break;
	case kDepthMode2:
		break;
	case kDepthMode3:
		break;
	case kDepthMode4:
		break;
	case kDepthMode5:
		break;
	case kDepthMode6:
		break;
	default:
		return paramErr;
	}
	
	SwapMMUMode ( &busMode );
	
	write_reg(dce, GOBOFB_VIDEOCTRL, 0); // here we know we're going to change something, disable video */
	
	if (mode != dStore->curMode) {
		UInt8 id = mode - nativeVidMode;
		unsigned short i;
		for (i = nativeVidMode ; i <= dStore->maxMode ; i++) {
			// disable spurious resources, enable only the right one
			SpBlock spb;
			spb.spParamData = (i != mode ? 1 : 0); /* disable/enable */
			spb.spSlot = dStore->slot;
			spb.spID = i;
			spb.spExtDev = 0;
			SetSRsrcState(&spb);
		}
		dce->dCtlSlotId = mode; // where is that explained ? cscSwitchMode is not in DCDMF3, and you should'nt do that anymore says PDCD...
		
		unsigned int ho = ((dStore->hres[0] - dStore->hres[id]) / 2);
		unsigned int vo = ((dStore->vres[0] - dStore->vres[id]) / 2);
		
#if defined(ENABLE_HDMI_ALT_CHANGE)
		// we have the ability to change the hardware resolution
		uint32_t a32 = dce->dCtlDevBase;
		
		// here so that data aren't global
		// timings for the VTG
#include "NuBusFPGADrvr_Timings.h"

		const uint8_t reg_addr[12] = { DIV_REG, CLKFBOUT_REG1, CLKFBOUT_REG2,
					 LOCK_REG1, LOCK_REG2, LOCK_REG3,
					 FILT_REG1, FILT_REG2,
					 CLKOUT0_REG1, CLKOUT0_REG2,
					 CLKOUT1_REG1, CLKOUT1_REG2 };
		const uint16_t reg_mask[12] = { KEEP_IN_DIV, KEEP_IN_MUL_REG1, KEEP_IN_MUL_REG2,
					  LOCK1_MASK, LOCK23_MASK, LOCK23_MASK,
					  FILT1_MASK, FILT2_MASK,
					  REG1_FREQ_MASK & REG1_PHASE_MASK, REG2_FREQ_MASK & REG2_PHASE_MASK,
					  REG1_FREQ_MASK & REG1_PHASE_MASK, REG2_FREQ_MASK & REG2_PHASE_MASK };
 
#if defined(ENABLE_HDMI_ALT_CHANGE_54MHZ)
		 const uint16_t freq_25175000[12]  = {0x1041, 0x28b, 0x80, 0x1db, 0x7c01, 0x7fe9, 0x9000, 0x100, 0x597, 0x80, 0x105, 0x80};
		 const uint16_t freq_40000000[12]  = {0x41, 0x493, 0x80, 0xfa, 0x7c01, 0x7fe9, 0x900, 0x1000, 0x30d, 0x80, 0x83, 0x80};
		 const uint16_t freq_65000000[12]  = {0x1041, 0x249, 0x0, 0x226, 0x7c01, 0x7fe9, 0x9900, 0x1100, 0x1c8, 0x80, 0x42, 0x80};
		 const uint16_t freq_108000000[12] = {0x1041, 0x28a, 0x0, 0x1f4, 0x7c01, 0x7fe9, 0x9000, 0x100, 0x145, 0x0, 0x41, 0x0};
		 const uint16_t freq_148500000[12] = {0x82, 0x6dc, 0x80, 0xfa, 0x7c01, 0x7fe9, 0x1100, 0x1800, 0x83, 0x80, 0x41, 0x40};
#elif defined(ENABLE_HDMI_ALT_CHANGE_48MHZ)
		 const uint16_t freq_25175000[12]  = {0x1041, 0x28b, 0x80, 0x1db, 0x7c01, 0x7fe9, 0x9000, 0x100, 0x514, 0x0, 0x104, 0x0};
		 const uint16_t freq_40000000[12]  = {0x1041, 0x30d, 0x80, 0x190, 0x7c01, 0x7fe9, 0x1100, 0x9000, 0x3cf, 0x0, 0xc3, 0x0};
		 const uint16_t freq_65000000[12]  = {0x41, 0x34e, 0x80, 0x15e, 0x7c01, 0x7fe9, 0x900, 0x1000, 0x145, 0x0, 0x41, 0x0};
		 const uint16_t freq_108000000[12] = {0x41, 0x597, 0x80, 0xfa, 0x7c01, 0x7fe9, 0x800, 0x8000, 0x145, 0x0, 0x41, 0x0};
		 const uint16_t freq_148500000[12] = {0x41, 0x3d0, 0x80, 0x12c, 0x7c01, 0x7fe9, 0x900, 0x1000, 0x83, 0x80, 0x41, 0x40};
#else
#error "Unknown input clock for MMCM"
#endif

		short timeout = 1000;
		while ((read_reg(dce, GOBOFB_VIDEOCTRL) & 0x2 != 0) && timeout) {
		  /* wait for the reset process to be over */
		  /* otherwise without a clock it won't finish */
		  timeout --;
		  delay(100);
		}

		if (timeout == 0)
		  err = ioErr;
		// first reset the MCMM and set new values
		litex_clk_assert_reg(DRP_RESET);
		
		const uint16_t* freq = freq_148500000;
		const struct vtg_timing_regs *vtgtr = &vtg_1920x1080_60Hz;
		
		if (id & 0x1) {
		  switch (dStore->hres[id]) {
		  case 640:
		    freq = freq_25175000;
		    vtgtr = &vtg_640x480_60Hz;
		    ho = 0; /* full screen, not centered */
		    vo = 0;
		    break;
		  case 800:
		    freq = freq_40000000;
		    vtgtr = &vtg_800x600_60Hz;
		    ho = 0;
		    vo = 0;
		    break;
		  case 1024:
		    freq = freq_65000000;
		    vtgtr = &vtg_1024x768_60Hz;
		    ho = 0;
		    vo = 0;
		    break;
		  case 1280:
		    freq = freq_108000000;
		    vtgtr = &vtg_1280x1024_60Hz;
		    ho = 0;
		    vo = 0;
		    break;
		  default:
		    break;
		  }
		}
		
		for (int i = 0; (i < 12) && (err == noErr); i++) {
		  err = litex_clk_change_value_norst(a32,
						     reg_mask[i], freq[i],
						     reg_addr[i]);
		  if (err != noErr) goto mmcmdone;
		}
		
		litex_clk_deassert_reg(DRP_RESET);
		
		err = litex_clk_wait(dce->dCtlDevBase, DRP_LOCKED);
		if (err != noErr) goto mmcmdone;
		
		/* the clock should be back we can finish */

		// second fully reconfigure the VTG
		goblin_video_framebuffer_vtg_hres_write(a32,        vtgtr->hres);
		goblin_video_framebuffer_vtg_hsync_start_write(a32, vtgtr->hsync_start);
		goblin_video_framebuffer_vtg_hsync_end_write(a32,   vtgtr->hsync_end);
		goblin_video_framebuffer_vtg_hscan_write(a32,       vtgtr->hscan);
		goblin_video_framebuffer_vtg_vres_write(a32,        vtgtr->vres);
		goblin_video_framebuffer_vtg_vsync_start_write(a32, vtgtr->vsync_start);
		goblin_video_framebuffer_vtg_vsync_end_write(a32,   vtgtr->vsync_end);
		goblin_video_framebuffer_vtg_vscan_write(a32,       vtgtr->vscan);
 
	mmcmdone:
		; /* nothing */
#endif
		/* center picture in frame */
		write_reg(dce, GOBOFB_HRES_START, __builtin_bswap32(ho));
		write_reg(dce, GOBOFB_VRES_START, __builtin_bswap32(vo));
		write_reg(dce, GOBOFB_HRES_END, __builtin_bswap32(ho + dStore->hres[id]));
		write_reg(dce, GOBOFB_VRES_END, __builtin_bswap32(vo + dStore->vres[id]));
	}
	
	if (depth != dStore->curDepth) {
		switch (depth) {
		case kDepthMode1:
			write_reg(dce, GOBOFB_MODE, GOBOFB_MODE_8BIT);
			break;
		case kDepthMode2:
			write_reg(dce, GOBOFB_MODE, GOBOFB_MODE_4BIT);
			break;
		case kDepthMode3:
			write_reg(dce, GOBOFB_MODE, GOBOFB_MODE_2BIT);
			break;
		case kDepthMode4:
			write_reg(dce, GOBOFB_MODE, GOBOFB_MODE_1BIT);
			break;
		case kDepthMode5:
			write_reg(dce, GOBOFB_MODE, GOBOFB_MODE_24BIT);
			break;
		case kDepthMode6:
			write_reg(dce, GOBOFB_MODE, GOBOFB_MODE_15BIT);
			break;
		default:
			SwapMMUMode ( &busMode );
			return paramErr;
		}
	}
	dStore->curMode = mode;
	dStore->curDepth = depth;
	dStore->curPage = page; /* FIXME: HW */

	short timeout = 1000;
	while ((read_reg(dce, GOBOFB_VIDEOCTRL) & 0x2 != 0) && timeout) {
	  /* wait for the reset process to be over */
	  timeout --;
	}
	if (timeout == 0)
	  err = ioErr;
	
	write_reg(dce, GOBOFB_VIDEOCTRL, 1); // restart the video with the new parameters
		  
	SwapMMUMode ( &busMode );

	return err;
}

OSErr updatePRAM(AuxDCEPtr dce, unsigned char mode, unsigned char depth, unsigned short page) {
	NuBusFPGADriverGlobalsHdl dStoreHdl = (NuBusFPGADriverGlobalsHdl)dce->dCtlStorage;
	NuBusFPGADriverGlobalsPtr dStore = *dStoreHdl;
	const short npage = (depth == kDepthMode5) ? 1 : 2;
	SpBlock spb;
	NuBusFPGAPramRecord pram;
	OSErr err;
		  
	if (page >= npage)
		return paramErr;

	if ((mode < nativeVidMode) ||
		(mode > dStore->maxMode))
		return paramErr;
		  
	switch (depth) {
	case kDepthMode1:
		break;
	case kDepthMode2:
		break;
	case kDepthMode3:
		break;
	case kDepthMode4:
		break;
	case kDepthMode5:
		break;
	case kDepthMode6:
		break;
	default:
		return paramErr;
	}

	spb.spSlot = dce->dCtlSlot;
	spb.spResult = (UInt32)&pram;
	err = SReadPRAMRec(&spb);
	if (err == noErr) {
		pram.mode = mode;
		pram.depth = depth;
		pram.page = page;
		spb.spSlot = dce->dCtlSlot;
		spb.spsPointer = (Ptr)&pram;
		err = SPutPRAMRec(&spb);
	}
	return err;
}
