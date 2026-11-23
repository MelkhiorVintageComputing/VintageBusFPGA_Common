	.include "atrap.inc"
	.include "globals.inc"
	.include "declrom.inc"

	.include "ROMDefs.inc"
	.include "Video.inc"
	.include "DepVideo.inc"

sRsrc_Board = 1 /*  board sResource (>0 & <128) */
	.include "VidRomDef.s"
sRsrc_RAMDsk = 0xF0 /*  functional sResources */
sRsrc_SDCard = 0xF1 /*  functional sResources */
sRsrc_HDMIAudio = 0xA0 /*  functional sResources */
	
    .global DeclROMDir

    .section .text.begin

	.include "VidRomRsrcDir.s"

    .global _sRsrc_Board
_sRsrc_Board:	
    OSLstEntry  sRsrcType,_BoardType       /*  offset to board descriptor */
    OSLstEntry  sRsrcName,_BoardName       /*  offset to name of board */
    DatLstEntry boardId,NuBusFPGAID         /*  board ID # (assigned by DTS) */
    /* OSLstEntry  primaryInit,_sPInitRec */    /*  offset to PrimaryInit exec blk */
	.long entry_sPInitRec
    OSLstEntry  vendorInfo,_VendorInfo     /*  offset to vendor info record */
	/* OSLstEntry  secondaryInit,_sSInitRec */  /* offset to SecondaryInit block	 */
	.long entry_sSInitRec
	OSLstEntry	sRsrcVidNames, _VModeName /* video name directory */
	.long EndOfList

_BoardType:	
    .short catBoard            /*  board sResource */
    .short typeBoard
    .short 0
    .short 0
	
_BoardName: 
    .string "NuBusFPGA GoboFB\0" /*  name of board */
	ALIGN 2

/*  _VidICON ; optional icon, not needed */

	.section .text.primary_init
/* _sPInitRec: */
    /* .long       _EndsPInitRec-_sPInitRec */ /*  physical block size */
	.long size_sPInitRec
	.byte	sExec2						/* Code revision (Primary init) */
	.byte	sCPU68020					/* CPU type is 68020 */
	.short	0							/* Reserved */
	.long	Primary-.					/* Offset to C code. */
    ALIGN 2
/* _EndsPInitRec: */

	.section .text.secondary_init
/* _sSInitRec: */
    /* .long    _EndsSInitRec-_sSInitRec */ /* physical block size */
	.long size_sSInitRec
	.byte	sExec2						/* Code revision (Primary init) */
	.byte	sCPU68020					/* CPU type is 68020 */
	.short	0							/* Reserved */
	.long	Secondary-.					/* Offset to C code. */
    ALIGN 2
/* _EndsSInitRec: */

    .section .text.begin
	ALIGN 2
_VendorInfo:	
    OSLstEntry vendorId,_VendorId      /*  offset to vendor ID */
    OSLstEntry serialNum,_SerialNum      /*  offset to revision */
    OSLstEntry revLevel,_RevLevel      /*  offset to revision */
    OSLstEntry partNum,_PartNum        /*  offset to part number record */
    OSLstEntry date,_Date              /*  offset to ROM build date */
    .long EndOfList
	
_VendorId:	
            .string        "Romain Dolbeau\0"        /*  vendor ID */
_SerialNum:	
            .string        "0000000001\0"        /*  serial number */
_RevLevel:
	.include "../../board.inc"
_PartNum:	
            .string        "Part Number\0"           /*  part number */
_Date:	
    .string        "&SysDate"              /*  date */

	.include "VidRomName.s" /* contains _VidName */

	.include "VidRomDir.s"

	ALIGN 2
_GoboFBType:	
    .short        catDisplay               /*      <Category> */
    .short        typeVideo                 /*      <Type> */
    .short        drSwApple                /*      <DrvrSw> */
    .short        DrHwNuBusFPGA             /*      <DrvrHw> */
			  
_GoboFBName:	
    .string        "GoboFB_NuBusFPGA"        /*  video driver name */
	
_MinorBase:	
    .long        defMinorBase             /*  frame buffer offset */
_MinorLength:	
    .long        defMinorLength           /*  frame buffer length */

	ALIGN 2
	.section .text.begin
	.global _GoboFBDrvrDir
_GoboFBDrvrDir:	
    /* OSLstEntry  sMacOS68020,_GoboFBDrvrMacOS68020  */   /* driver directory for Mac OS */
	.long entry_GoboFBDrvrMacOS68020
    .long EndOfList 

	ALIGN 2
	.section .text.fbdriver_init
/* _GoboFBDrvrMacOS68020: */ /* supplied by linker script */
    .long        _GoboFBEnd020Drvr-.   /*  physical block size */
    .include     "NuBusFPGADrvr.s"             /*   driver code */
/* _GoboFBEnd020Drvr: */ /* supplied by linker script */
	
	.section .text.begin
	.include "VidRomRes.s"
/* ////////////////////////////////////////////// RAM DISK */
	.section .text.begin
	ALIGN 2
_sRsrc_RAMDsk:	
	OSLstEntry  sRsrcType,_RAMDskType      /*  video type descriptor */
    OSLstEntry  sRsrcName,_RAMDskName      /*  offset to driver name string */
    OSLstEntry  sRsrcDrvrDir,_RAMDskDrvrDir /* offset to driver directory */
	DatLstEntry  sRsrcFlags,6    /* force 32 bits mode & open */
    DatLstEntry sRsrcHWDevId,2           /*  hardware device ID */
    .long EndOfList               /*  end of list */

	ALIGN 2
_RAMDskType:	
    .short        catProto               /*      <Category> */
    .short        typeDrive /* custom */                 /*      <Type> */
    .short        drSwApple                /*      <DrvrSw> */
    .short        DrHwNuBusFPGADsk             /*      <DrvrHw> */
			  
_RAMDskName:	
    .string        "RAMDsk_NuBusFPGA"        /*  video driver name */
	
	ALIGN 2
	.section .text.begin
	.global _RAMDskDrvrDir
_RAMDskDrvrDir:	
    /* OSLstEntry  sMacOS68020,_RAMDskDrvrMacOS68020 */    /* driver directory for Mac OS */
	.long entry_RAMDskDrvrMacOS68020
    .long EndOfList 

	ALIGN 2
	.section .text.dskdriver_init
/* _RAMDskDrvrMacOS68020: */ /* supplied by linker script */
    .long        _RAMDskEnd020Drvr-.   /*  physical block size */
    .include     "NuBusFPGARAMDskDrvr.s"             /*   driver code */
/* _RAMDskEnd020Drvr: */ /* supplied by linker script */

/* ////////////////////////////////////////////// SDCARD */
	.ifdef ENABLE_SDCARD /* --defsym from the Makefile when -DENABLE_SDCARD is in FEATURES */
	.section .text.begin
	ALIGN 2
_sRsrc_SDCard:	
	OSLstEntry  sRsrcType,_SDCardType      /*  video type descriptor */
    OSLstEntry  sRsrcName,_SDCardName      /*  offset to driver name string */
    OSLstEntry  sRsrcDrvrDir,_SDCardDrvrDir /* offset to driver directory */
	.ifndef SDCARD_NO_BOOTREC /* --defsym SDCARD_NO_BOOTREC=1 to build without */
	OSLstEntry  sRsrcBootRec,_SDCardBootRec /* boot record: startup from the SD card */
	.endif
	DatLstEntry  sRsrcFlags,6    /* force 32 bits mode & open */
    DatLstEntry sRsrcHWDevId,3           /*  hardware device ID (unique on the card: RAM disk is 2) */
    .long EndOfList               /*  end of list */

/* sBootRecord (DCD3 p.168, PDF 209; IM V-422/423). Called with A0 = seBlock:
   - seBootState = 0, early in the ROM startup, only when PRAM's default startup device
     names this slot/sResource: open the driver (its Open initializes the card and adds
     the drive), return the driver refNum in seRefNum and seStatus = 0 (negative = no
     driver, the normal startup then happens); the ROM then reads the boot blocks from
     that drive;
   - seBootState = 1, after the system patches: "must open any remaining drivers for
     devices on the card". Observed on a Quadra: with a boot record, the SD driver is not
     opened by the usual fOpenAtStart pass any more (even when starting from the internal
     drive), so open it here (harmless if already open: Open isn't called again).
   Modelled on the NS 8/16 ROM (ns816-declrom/ns816_quadra.s). Holding Option at startup
   skips the card in the first call. The block must be self-contained (copied to RAM). */
/* local offsets (the .inc files define several structs with the same field names) */
sdb_ioCompletion = 12
sdb_ioNamePtr = 18
sdb_ioRefNum = 24
sdb_ioPermssn = 27
sdb_ioMix = 28 /* SlotDevParam: for the driver's use */
sdb_ioFlags = 32 /* SlotDevParam ioFlags, ioSlot (34), ioID (35) */
sdb_ioSlot = 34
sdb_ioID = 35
sdb_pbSize = 50 /* HParamBlockRec size */
sdb_qHead = 2 /* QHdr */
sdb_qLink = 0 /* DrvQEl */
sdb_dQDrive = 6
sdb_dQRefNum = 8
sdb_seSlot = 0
sdb_seRsrcID = 1
sdb_seStatus = 2
sdb_seRefNum = 20
sdb_seBootState = 22
SDCARD_BOOT_MAGIC = 0x53446274 /* 'SDbt', see NuBusFPGASDCardDrvr.h */

	ALIGN 2
_SDCardBootRec:	/* SExecBlock */
	.long _SDCardBootRecEnd-_SDCardBootRec /* block size */
	.byte 2 /* revision level */
	.byte cpu68020 /* CPU type */
	.short 0 /* reserved */
	.long _SDCardBootCode-. /* code offset */
_SDCardBootCode:
	moveml %d1-%fp,%sp@-
	moveal %a0,%a2 /* a2 = seBlock */
	subaw #sdb_pbSize,%sp
	moveal %sp,%a3 /* a3 = param block */
	lea %pc@(_SDCardBootDrvrName),%a1
	moveb %a2@(sdb_seRsrcID),%d2
	tstb %a2@(sdb_seBootState)
	bnew 5f
	/* first call: open the SD driver, it adds the drive the ROM will start from */
	btst #2,KeyMap+7 /* Option key down: don't start from the card */
	bnew 8f
	movel #SDCARD_BOOT_MAGIC,%d3 /* tells the driver's Open it's the boot open */
	bsrw 20f
	bnew 8f
	/* find the drive the driver added */
	moveal DrvQHdr+sdb_qHead,%a0
1:	cmpal #0,%a0
	beqw 8f /* no drive: the card wasn't usable */
	cmpw %a0@(sdb_dQRefNum),%d1
	beqs 2f
	moveal %a0@(sdb_qLink),%a0
	bras 1b
2:	/* disk-inserted event, as the NS 8/16 does, so the volume gets mounted even if the
	   ROM ends up starting from another drive (harmless otherwise) */
	tstw EvtBufCnt
	bles 3f
	moveq #0,%d0
	movew %a0@(sdb_dQDrive),%d0
	moveaw #7,%a0 /* diskEvt */
	_PostEvent
3:	moveb %d1,%a2@(sdb_seRefNum) /* refNums of unit table entries fit in a signed byte */
	clrw %a2@(sdb_seStatus)
	bras 9f
5:	/* second call: open the SD driver (normal open, it mounts the volume); errors ignored */
	moveq #0,%d3
	bsrw 20f
	clrw %a2@(sdb_seStatus)
	bras 9f
8:	movew #openErr,%a2@(sdb_seStatus)
9:	addaw #sdb_pbSize,%sp
	moveml %sp@+,%d1-%fp
	rts
/* _HOpen driver: a1 = name, d2.b = sResource ID, d3 = ioMix value, a2 = seBlock,
   a3 = param block; returns d0 = result (flags set), d1 = refNum */
20:	moveal %a3,%a0
	clrl %a0@(sdb_ioCompletion)
	movel %a1,%a0@(sdb_ioNamePtr)
	moveb #fsRdWrPerm,%a0@(sdb_ioPermssn)
	movel %d3,%a0@(sdb_ioMix)
	clrw %a0@(sdb_ioFlags)
	moveb %a2@(sdb_seSlot),%a0@(sdb_ioSlot)
	moveb %d2,%a0@(sdb_ioID)
	_HOpen
	movew %a0@(sdb_ioRefNum),%d1
	tstw %d0
	rts
_SDCardBootDrvrName:
	.byte _SDCardBootDrvrNameEnd-.-1 /* pascal string, must match the driver header name */
	.ascii ".NuBusFPGASDCard_Drvr"
_SDCardBootDrvrNameEnd:
	ALIGN 2
_SDCardBootRecEnd:

	ALIGN 2
_SDCardType:	
    .short        catProto               /*      <Category> */
    .short        typeDrive /* custom */                 /*      <Type> */
    .short        drSwApple                /*      <DrvrSw> */
    .short        DrHwNuBusFPGASDCard             /*      <DrvrHw> */
			  
_SDCardName:	
    .string        "SDCard_NuBusFPGA"        /*  video driver name */
	
	ALIGN 2
	.section .text.begin
	.global _SDCardDrvrDir
_SDCardDrvrDir:	
    /* OSLstEntry  sMacOS68020,_SDCardDrvrMacOS68020 */    /* driver directory for Mac OS */
	.long entry_SDCardDrvrMacOS68020
    .long EndOfList 

	ALIGN 2
	.section .text.sddriver_init
/* _SDCardDrvrMacOS68020: */ /* supplied by linker script */
    .long        _SDCardEnd020Drvr-.   /*  physical block size */
    .include     "NuBusFPGASDCardDrvr.s"             /*   driver code */
/* _SDCardEnd020Drvr: */ /* supplied by linker script */
	.endif /* ENABLE_SDCARD */

	
/* ////////////////////////////////////////////// HDMI AUDIO */
	.section .text.begin
	.include "goblin_param.inc"
	ALIGN 2
_sRsrc_HDMIAudio:	
	OSLstEntry  sRsrcType,_HDMIAudioType      /*  video type descriptor */
	OSLstEntry  0xd0,_HDMIAudioInfo
	/* no driver */
    .long EndOfList               /*  end of list */

	ALIGN 2
_HDMIAudioType:	
    .short        catProto               /*      <Category> */
    .short        typeAudio /* custom */                 /*      <Type> */
    .short        drSwApple                /*      <DrvrSw> */
	.short        DrHwNuBusFPGAAudio             /*      <DrvrHw> */

	ALIGN 2
_HDMIAudioInfo:	
	.long csr_goblin_base /* where to find the CSR */
	.long goblin_audiobuffer_offset
	.long goblin_audiobuffer_size
	
/* ////////////////////////////////////////////// DECLARION ROM */
    /* Declaration ROM directory at end */
       .section .romblock
       ALIGN 2
DeclROMDir:
       .long RsrcDirOffset /* supplied by linker script, replace OSLstEntry 0, _sRsrcDir */
DeclROMCRC:
       .long ROMSize /* supplied by linker script */
       .long 0 /* crc TBComputed after the fact */
       .byte 1                  /* Revision Level */
       .byte appleFormat        /* Apple Format */
       .long testPattern        /* magic TestPattern */
       .byte 0                  /* reserved */
       .byte 0x0F               /* byte lane marker */
DeclRomEnd:
       .end
