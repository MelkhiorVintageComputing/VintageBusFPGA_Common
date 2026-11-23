#ifndef __NUBUSFPGARAMDSKDRVR_H__
#define __NUBUSFPGARAMDSKDRVR_H__

#include <Files.h>
#include <Devices.h>
#include <Slots.h>
#include <MacErrors.h>
#include <MacMemory.h>
#include <Disks.h>

#include "NuBusFPGADrvr.h"

struct SDCardContext {
  DrvSts2 drvsts;           /* must stay first, contains the drive queue element */
  uint32_t sc;              /* dCtlDevBase, 0xFs000000 */
  uint32_t size_blk;        /* card size in 512-byte blocks (capped) */
  uint16_t rca;             /* relative card address */
  char slot;
  unsigned char hc;         /* 1 for SDHC/SDXC (block addressing), 0 for SDSC (byte addressing) */
  unsigned char fence;      /* sequence number for sdcard_fence() */
  unsigned char dead;       /* SD core stuck (no hardware timeout on some states), device unusable */
  unsigned char wr_broken;  /* write DMA FIFO may hold stale data, writes refused */
  unsigned char guard;      /* NuBus reads to wait before a command, covers 8 SD clocks */
  unsigned char v2;         /* answered CMD8 (physical layer 2.00+) */
  uint16_t hs_status;       /* CMD6 function group 1 result (1 = High Speed), 0xFFFF if unknown */
  uint16_t divider;         /* SD clock = sys_clk (100 MHz) / divider */
  uint32_t read_retries;
  uint32_t write_retries;
  /* returned by Control csCode 21/22 (IM V-470): 32x32 icon, mask, then the Pascal
     string shown after "Where:" in Get Info (21 only); must stay valid after the call */
  unsigned char icon[256 + 32];
};

/* set in ioMix (SlotDevParam ioSMix in Retro68, offset 28, for the driver's use) by the
   sBootRecord's first _HOpen (vid_decl_rom.s), so Open knows it's called early in the
   ROM startup */
#define SDCARD_BOOT_MAGIC 0x53446274 /* 'SDbt' */

/* driver-specific Status/Control calls, for diagnostics (see SDTest) */
#define kSDCardInfo     200 /* Status: csParam <- struct SDCardInfo */
#define kSDCardSetClock 200 /* Control: csParam = long, SD clock divider (power of 2, 2-256) */
#define kSDCardSetSpeed 201 /* Control: csParam = long, 0 = default speed, 1 = High Speed (CMD6) */
struct SDCardInfo {
  uint16_t version;         /* 1 */
  uint16_t flags;           /* bit 0 hc, bit 1 v2, bit 2 dead, bit 3 wr_broken */
  uint16_t hs_status;
  uint16_t divider;
  uint32_t read_retries;
  uint32_t write_retries;
  uint32_t size_blk;
}; /* 20 bytes, must fit in csParam (22) */

#include "nubusfpga_csr_common.h"

#if defined(NUBUSFPGA)
#include "../../nubusfpga_csr_sdblock2mem.h"
#include "../../nubusfpga_csr_sdcore.h"
#include "../../nubusfpga_csr_sdirq.h"
#include "../../nubusfpga_csr_sdmem2block.h"
#include "../../nubusfpga_csr_sdphy.h"
//#include "../../nubusfpga_csr_exchange_with_sd.h"
#elif defined(IISIFPGA)
#include "../../iisifpga_csr_sdblock2mem.h"
#include "../../iisifpga_csr_sdcore.h"
//#include "../../iisifpga_csr_sdirq.h"
#include "../../iisifpga_csr_sdmem2block.h"
#include "../../iisifpga_csr_sdphy.h"
//#include "../../iisifpga_csr_exchange_with_sd.h"
#elif defined(LC32FPGA)
#include "../../lc32fpga_csr_sdblock2mem.h"
#include "../../lc32fpga_csr_sdcore.h"
//#include "../../lc32fpga_csr_sdirq.h"
#include "../../lc32fpga_csr_sdmem2block.h"
#include "../../lc32fpga_csr_sdphy.h"
//#include "../../lc32fpga_csr_exchange_with_sd.h"
#elif defined(QUADRAFPGA)
#include "../../quadrafpga_csr_sdblock2mem.h"
#include "../../quadrafpga_csr_sdcore.h"
//#include "../../quadrafpga_csr_sdirq.h"
#include "../../quadrafpga_csr_sdmem2block.h"
#include "../../quadrafpga_csr_sdphy.h"
//#include "../../quadrafpga_csr_exchange_with_sd.h"
#else
#error "no board defined"
#endif

/* basically Litex BIOS code */

#ifndef CONFIG_CLOCK_FREQUENCY
#define CONFIG_CLOCK_FREQUENCY 100000000
#endif


#define CLKGEN_STATUS_BUSY		0x1
#define CLKGEN_STATUS_PROGDONE	0x2
#define CLKGEN_STATUS_LOCKED	0x4

#define SD_CMD_RESPONSE_SIZE 16

#define SD_OK         0
#define SD_CRCERROR   1
#define SD_TIMEOUT    2
#define SD_WRITEERROR 3
#define SD_HWHANG     4 /* the SD core never completed, nothing more can be done until FPGA reset */
#define SD_CARDERROR  5 /* the card reported an error in its R1 status */

/* staging buffer, dedicated SRAM in the gateware ("sd_buf" in MacPeriphSoC.py) */
#define SDCARD_BUF_OFFSET   0x00904000 /* from dCtlDevBase (CPU side) */
#define SDCARD_BUF_DMA_ADDR 0xF0904000 /* Wishbone address (DMA side) */
#define SDCARD_BUF_SIZE     16384
#define SDCARD_MAX_BLK_PER_OP (SDCARD_BUF_SIZE/512)

/* Timeouts. The hardware command/data/busy timeouts are 1 s each, so these only
   trigger when the SD core is stuck (some PHY states have no hardware timeout).
   Measured in Ticks (60 Hz); in case Ticks doesn't advance (interrupts masked),
   there is also a cap in loop iterations: every iteration does at least one
   NuBus read, which takes at least 200 ns, so (ticks << 16) iterations is
   always longer than the tick limit. */
#define SD_TICKS_CMD          120 /* 2 s */
#define SD_TICKS_PER_BLK_SHIFT  5 /* (n << 5) ticks, ~0.5 s per block for data commands */
#define SD_TICKS_TRAN          60 /* 1 s for the card to finish programming (SDHC max 250 ms, SDXC 500 ms) */
#define SD_POLL_FENCE     100000ul  /* iterations, >= 20 ms */
#define SD_POLL_DMA      1000000ul  /* iterations, >= 200 ms, DMA after the SD core finished */

/* After a response without data, the PHY keeps clocking 8 cycles with CMD driven high
   while the core already reports 'done'; a command sent during those would have its
   first bits forced to 1. sdcard_send_command waits ctx->guard NuBus reads (>= 200 ns
   each) first, set from the clock divider by sdcard_set_divider. */

#define SD_RETRIES 3

/* R1 card status error bits we check (ILLEGAL_COMMAND and COM_CRC_ERROR are left out,
   they refer to the previous command) */
#define SD_R1_ERRORS 0xFC380000ul /* OUT_OF_RANGE ADDRESS_ERROR BLOCK_LEN_ERROR ERASE_SEQ_ERROR ERASE_PARAM WP_VIOLATION CARD_ECC_FAILED CC_ERROR ERROR */
#define SD_R1_STATE(r1) (((r1) >> 9) & 0xF)
#define SD_R1_STATE_TRAN 4

#define SDPHY_DATAW_STATUS_ACCEPTED 0x1

#define SD_SWITCH_CHECK  0
#define SD_SWITCH_SWITCH 1

#define SD_SPEED_SDR12  0
#define SD_SPEED_SDR25  1
#define SD_SPEED_SDR50  2
#define SD_SPEED_SDR104 3
#define SD_SPEED_DDR50  4

#define SD_DRIVER_STRENGTH_B 0
#define SD_DRIVER_STRENGTH_A 1
#define SD_DRIVER_STRENGTH_C 2
#define SD_DRIVER_STRENGTH_D 3

#define SD_GROUP_ACCESSMODE     0
#define SD_GROUP_COMMANDSYSTEM  1
#define SD_GROUP_DRIVERSTRENGTH 2
#define SD_GROUP_POWERLIMIT     3

#define SDCARD_STREAM_STATUS_OK           0b000
#define SDCARD_STREAM_STATUS_TIMEOUT      0b001
#define SDCARD_STREAM_STATUS_DATAACCEPTED 0b010
#define SDCARD_STREAM_STATUS_CRCERROR     0b101
#define SDCARD_STREAM_STATUS_WRITEERROR   0b110

#define SDCARD_CTRL_DATA_TRANSFER_NONE  0
#define SDCARD_CTRL_DATA_TRANSFER_READ  1
#define SDCARD_CTRL_DATA_TRANSFER_WRITE 2

#define SDCARD_CTRL_RESPONSE_NONE       0
#define SDCARD_CTRL_RESPONSE_SHORT      1
#define SDCARD_CTRL_RESPONSE_LONG       2
#define SDCARD_CTRL_RESPONSE_SHORT_BUSY 3

//#define SDCARD_DEBUG
/* no CMD23 (SET_BLOCK_COUNT): optional for most cards, and redundant with the CMD12 we always send */
//#define SDCARD_CMD23_SUPPORT /* SET_BLOCK_COUNT */
#define SDCARD_CMD18_SUPPORT /* READ_MULTIPLE_BLOCK */
#define SDCARD_CMD25_SUPPORT /* WRITE_MULTIPLE_BLOCK */

#ifndef SDCARD_CLK_FREQ_INIT
#define SDCARD_CLK_FREQ_INIT 400000
#endif

#ifndef SDCARD_CLK_FREQ
#define SDCARD_CLK_FREQ 25000000
//#define SDCARD_CLK_FREQ 12500000
#endif
/* power-of-2 divider of the 100 MHz sys_clk: 4 = 25 MHz, 8 = 12.5 MHz (runtime: kSDCardSetClock) */
/* define to use High Speed mode (see sdcard_init: unreliable with the LiteX PHY sampling point) */
//#define SDCARD_USE_HIGH_SPEED
#ifndef SDCARD_CLK_DIVIDER
#define SDCARD_CLK_DIVIDER 4
#endif


/* ctrl */
OSErr cNuBusFPGASDCardCtl(CntrlParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce) __attribute__ ((section (".text.sddriver")));
/* open, close */
OSErr cNuBusFPGASDCardOpen(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce) __attribute__ ((section (".text.sddriver")));
OSErr cNuBusFPGASDCardClose(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce) __attribute__ ((section (".text.sddriver")));
void busy_wait(int d) __attribute__ ((section (".text.sddriver")));
void delay(int d) __attribute__ ((section (".text.sddriver")));
int sdcard_read(struct SDCardContext *ctx, uint32_t block, uint32_t count, uint8_t* buf) __attribute__ ((section (".text.sddriver")));
int sdcard_write(struct SDCardContext *ctx, uint32_t block, uint32_t count, uint8_t* buf) __attribute__ ((section (".text.sddriver")));
void sdcard_set_divider(struct SDCardContext *ctx, uint32_t divider) __attribute__ ((section (".text.sddriver")));
int sdcard_set_speed(struct SDCardContext *ctx, int hs) __attribute__ ((section (".text.sddriver")));
/* prime */
OSErr cNuBusFPGASDCardPrime(IOParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce) __attribute__ ((section (".text.sddriver")));
void waitSome(unsigned long bound) __attribute__ ((section (".text.sddriver")));
/* status */
OSErr cNuBusFPGASDCardStatus(CntrlParamPtr pb, /* DCtlPtr */ AuxDCEPtr dce) __attribute__ ((section (".text.sddriver")));

uint32_t rledec(uint32_t* out, const uint32_t* in, const uint32_t len) __attribute__ ((section (".text.sddriver")));

#endif
