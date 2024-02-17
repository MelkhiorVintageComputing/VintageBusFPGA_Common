


/* MMCM specific numbers */
#define CLKOUT_MAX		7
#define DELAY_TIME_MAX		63
#define PHASE_MUX_MAX		7
#define HIGH_LOW_TIME_REG_MAX	63
#define PHASE_MUX_RES_FACTOR	8

/* DRP registers index */
#define DRP_RESET		0
#define DRP_LOCKED		1
#define DRP_READ		2
#define DRP_WRITE		3
#define DRP_DRDY		4
#define DRP_ADR			5
#define DRP_DAT_W		6
#define DRP_DAT_R		7


/* Register values */
#define FULL_REG_16		0xFFFF
#define ZERO_REG		0x0
#define KEEP_IN_MUL_REG1	0xF000
#define KEEP_IN_MUL_REG2	0xFF3F
#define KEEP_IN_DIV		0xC000
#define REG1_FREQ_MASK		0xF000
#define REG2_FREQ_MASK		0x803F
#define REG1_DUTY_MASK		0xF000
#define REG2_DUTY_MASK		0xFF7F
#define REG1_PHASE_MASK		0x1FFF
#define REG2_PHASE_MASK		0xFCC0
#define FILT1_MASK		0x66FF
#define FILT2_MASK		0x666F
#define LOCK1_MASK		0xFC00
#define LOCK23_MASK		0x8000
/* Control bits extraction masks */
#define HL_TIME_MASK		0x3F
#define FRAC_MASK		0x7
#define EDGE_MASK		0x1
#define NO_CNT_MASK		0x1
#define FRAC_EN_MASK		0x1
#define PHASE_MUX_MASK		0x7

/* Bit groups start position in DRP registers */
#define HIGH_TIME_POS		6
#define LOW_TIME_POS		0
#define PHASE_MUX_POS		13
#define FRAC_POS		12
#define FRAC_EN_POS		11
#define FRAC_WF_R_POS		10
#define EDGE_POS		7
#define NO_CNT_POS		6
#define EDGE_DIVREG_POS		13
#define NO_CNT_DIVREG_POS	12
#define DELAY_TIME_POS		0

/* MMCM Register addresses */
#define POWER_REG		0x28
#define DIV_REG			0x16
#define LOCK_REG1		0x18
#define LOCK_REG2		0x19
#define LOCK_REG3		0x1A
#define FILT_REG1		0x4E
#define FILT_REG2		0x4F
#define CLKOUT0_REG1		0x08
#define CLKOUT0_REG2		0x09
#define CLKOUT1_REG1		0x0A
#define CLKOUT1_REG2		0x0B
#define CLKOUT2_REG1		0x0C
#define CLKOUT2_REG2		0x0D
#define CLKOUT3_REG1		0x0E
#define CLKOUT3_REG2		0x0F
#define CLKOUT4_REG1		0x10
#define CLKOUT4_REG2		0x11
#define CLKOUT5_REG1		0x06
#define CLKOUT5_REG2		0x07
#define CLKOUT6_REG1		0x12
#define CLKOUT6_REG2		0x13
#define CLKFBOUT_REG1		0x14
#define CLKFBOUT_REG2		0x15

#define litex_clk_set_reg(a, b)    *((volatile uint32_t*)(a32 + CSR_CRG_VIDEO_PLL_##a##_ADDR + 0)) = __builtin_bswap32(b)
#define litex_clk_get_reg(a)       __builtin_bswap32(*((volatile uint32_t*)(a32 + CSR_CRG_VIDEO_PLL_##a##_ADDR)))
#define litex_clk_assert_reg(a)    *((volatile uint32_t*)(a32 + CSR_CRG_VIDEO_PLL_##a##_ADDR + 0)) = ((uint32_t)(-1))
#define litex_clk_deassert_reg(a)  *((volatile uint32_t*)(a32 + CSR_CRG_VIDEO_PLL_##a##_ADDR + 0)) = ((uint32_t)(0))

#define __ASSERT(a, b)
#define LOG_WRN(a, b)

static inline void mmcm_waitSome(unsigned long bound) {
  unsigned long i;
  for (i = 0 ; i < bound ; i++) {
    asm volatile("nop");
  }
}
static inline void delay(int d) {
  mmcm_waitSome(d * 20); // improveme
  return;
}

static inline int litex_clk_wait(uint32_t a32, uint32_t reg)
{
	uint32_t timeout;

	__ASSERT(reg == DRP_LOCKED || reg == DRP_DRDY, "Unsupported register! Please provide DRP_LOCKED or DRP_DRDY");

	if (reg == DRP_LOCKED) {
		timeout = 1000 /* ldev->timeout.lock */;
		while (!litex_clk_get_reg(DRP_LOCKED) && timeout) {
		  timeout--;
		  /* k_sleep(K_MSEC(1)); */
		  delay(5);
		}
	} else {
		timeout = 1000 /* ldev->timeout.drdy */;
		while (!litex_clk_get_reg(DRP_DRDY) && timeout) {
		  timeout--;
		  /* k_sleep(K_MSEC(1)); */
		  delay(5);
		}
	}
	/*Waiting for signal to assert in reg*/
	/* macro... can't use 'reg' */
	/* while (!litex_clk_get_reg(reg) && timeout) { */
	/* 	timeout--; */
	/* 	/\* k_sleep(K_MSEC(1)); *\/ */
	/*   delay(5); */
	/* } */
	if (timeout == 0) {
		LOG_WRN("Timeout occured when waiting for the register: 0x%x", reg);
		return ioErr;
	}
	return noErr;
}

/* Read value written in given internal MMCM register*/
static inline int litex_clk_get_DO(uint32_t a32, uint8_t clk_reg_addr, uint16_t *res)
{
	int ret = noErr;

	litex_clk_set_reg(DRP_ADR, clk_reg_addr);
	litex_clk_assert_reg(DRP_READ);

	litex_clk_deassert_reg(DRP_READ);
	ret = litex_clk_wait(a32, DRP_DRDY);
	if (ret != 0) {
		return ret;
	}

	*res = litex_clk_get_reg(DRP_DAT_R);

	return noErr;
}

/* Sets calculated DI value into DI DRP register */
static inline int litex_clk_set_DI(uint32_t a32, uint16_t DI_val)
{
	int ret = noErr;

	litex_clk_set_reg(DRP_DAT_W, DI_val);
	litex_clk_assert_reg(DRP_WRITE);
	litex_clk_deassert_reg(DRP_WRITE);
	ret = litex_clk_wait(a32, DRP_DRDY);
	return ret;
}

/* Returns raw value ready to be written into MMCM */
static inline uint16_t litex_clk_calc_DI(uint16_t DO_val, uint16_t mask,
							  uint16_t bitset)
{
	uint16_t DI_val;

	DI_val = DO_val & mask;
	DI_val |= bitset;

	return DI_val;
}

/*
 * Change register value as specified in arguments
 *
 * mask:		preserve or zero MMCM register bits
 *			by selecting 1 or 0 on desired specific mask positions
 * bitset:		set those bits in MMCM register which are 1 in bitset
 * clk_reg_addr:	internal MMCM address of control register
 *
 */
static inline int litex_clk_change_value_norst(uint32_t a32,
					       uint16_t mask, uint16_t bitset,
					       uint8_t clk_reg_addr)
{
	uint16_t DO_val, DI_val;
	int ret = noErr;

	//	litex_clk_assert_reg(DRP_RESET);

	ret = litex_clk_get_DO(a32, clk_reg_addr, &DO_val);
	if (ret != 0) {
		return ret;
	}
	DI_val = litex_clk_calc_DI(DO_val, mask, bitset);
	ret = litex_clk_set_DI(a32, DI_val);
	if (ret != 0) {
		return ret;
	}
#ifdef CONFIG_CLOCK_CONTROL_LOG_LEVEL_DBG
	DI_val = litex_clk_get_reg(DRP_DAT_W);
	LOG_DBG("set 0x%x under: 0x%x", DI_val, clk_reg_addr);
#endif
	litex_clk_deassert_reg(DRP_DAT_W);
	//	litex_clk_deassert_reg(DRP_RESET);
	//	ret = litex_clk_wait(DRP_LOCKED);
	return ret;
}
