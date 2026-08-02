#!/usr/bin/env python3

#https://gist.github.com/enjoy-digital/529a4d9994f0cc95e45382e4eb253b09

from migen import *

from VintageBusFPGA_Common.wb_master import *
from VintageBusFPGA_Common.wb_master import _WRITE_CMD, _WAIT_CMD, _DONE_CMD

dfii_control_sel     = 0x01
dfii_control_cke     = 0x02
dfii_control_odt     = 0x04
dfii_control_reset_n = 0x08

dfii_command_cs     = 0x01
dfii_command_we     = 0x02
dfii_command_cas    = 0x04
dfii_command_ras    = 0x08
dfii_command_wrdata = 0x10
dfii_command_rddata = 0x20

# bitslips and delays
#
# IIsiA7 Mini | bs | dl
# module 0    |  3 | 15
# module 1    |  3 | 14
    

def period_to_cycles(sys_clk_freq, period):
    return int(period*sys_clk_freq)

class DDR_Addr(WishboneMaster):
    def __init__(self, sdram_dfii_base, ddrphy_base):
        # /!\ keep up to date with csr /!\
        self.sdram_dfii_base = sdram_dfii_base
        self.sdram_dfii_control =           	self.sdram_dfii_base + 0x000
        self.sdram_dfii_pi0_command  =      	self.sdram_dfii_base + 0x004
        self.sdram_dfii_pi0_command_issue = 	self.sdram_dfii_base + 0x008
        self.sdram_dfii_pi0_address  =      	self.sdram_dfii_base + 0x00c
        self.sdram_dfii_pi0_baddress =      	self.sdram_dfii_base + 0x010

        # /!\ keep up to date with csr /!\
        self.ddrphy_base = ddrphy_base
        self.ddrphy_rst                 = self.ddrphy_base + 0x000
        self.ddrphy_dly_sel             = self.ddrphy_base + 0x004
        self.ddrphy_rdly_dq_rst         = self.ddrphy_base + 0x014
        self.ddrphy_rdly_dq_inc         = self.ddrphy_base + 0x018
        self.ddrphy_rdly_dq_bitslip_rst = self.ddrphy_base + 0x01c
        self.ddrphy_rdly_dq_bitslip     = self.ddrphy_base + 0x020
        self.ddrphy_wdly_dq_bitslip_rst = self.ddrphy_base + 0x024
        self.ddrphy_wdly_dq_bitslip     = self.ddrphy_base + 0x028
        self.ddrphy_rdphase             = self.ddrphy_base + 0x02c
        self.ddrphy_wdphase             = self.ddrphy_base + 0x030
        
    def startfb(self):
        r = []
        r += [_WRITE_CMD, 0xf0900008, 0x01000000] # FIXME: hardwired for now
        return r

    def ddr_config_instructions(self, bitslip, delay):
        r = []
        for module in range(2):
            r += [_WRITE_CMD, self.ddrphy_dly_sel, 1<<module ]
            r += [_WRITE_CMD, self.ddrphy_wdly_dq_bitslip_rst, 1<<module ] # checkme ? should be ?
            r += [_WRITE_CMD, self.ddrphy_dly_sel, 0 ]
        for module in range(2):
            r += [_WRITE_CMD, self.ddrphy_dly_sel, 1<<module ]
            r += [_WRITE_CMD, self.ddrphy_rdly_dq_bitslip_rst, 1]
            for i in range(bitslip[module]):
                r += [_WRITE_CMD, self.ddrphy_rdly_dq_bitslip, 1]
            r += [_WRITE_CMD, self.ddrphy_rdly_dq_rst, 1]
            for i in range(delay[module]):
                r += [_WRITE_CMD, self.ddrphy_rdly_dq_inc, 1]
            r += [_WRITE_CMD, self.ddrphy_dly_sel, 0 ]
        return r


class DDR3Addr(DDR_Addr):
    def __init__(self, sdram_dfii_base, ddrphy_base):
        DDR_Addr.__init__(self, sdram_dfii_base = sdram_dfii_base, ddrphy_base = ddrphy_base)

    def ddr3_init_instructions(self, sys_clk_freq):
        return [
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            # phase
            _WRITE_CMD, self.ddrphy_rdphase, 2,
            _WRITE_CMD, self.ddrphy_wdphase, 3,
            
            # software control
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_reset_n | dfii_control_odt | dfii_control_cke,
            
            # reset
            _WRITE_CMD, self.ddrphy_rst, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            _WRITE_CMD, self.ddrphy_rst, 0,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            
            # release reset
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_odt|dfii_control_reset_n,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.005),
            
            # bring cke high
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_cke|dfii_control_odt|dfii_control_reset_n,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            
            # load mode register 2, CWL = 5
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x200,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 2,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # load mode register 3
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 3,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # load mode register 1
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x6,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 1,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,

            # load mode register 0, CL=6, BL=8
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x920,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.0002),
            
            # zq calibration
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x400,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.0002),
            
            # hardware control
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_sel,
        ]

class DDR3Init(DDR3Addr):
    def __init__(self, sys_clk_freq, bitslip, delay, sdram_dfii_base, ddrphy_base):
        DDR3Addr.__init__(self, sdram_dfii_base = sdram_dfii_base, ddrphy_base = ddrphy_base)
        WishboneMaster.__init__(self,
            self.ddr3_init_instructions(sys_clk_freq) +
            self.ddr_config_instructions(bitslip, delay) +
            [_DONE_CMD])

class DDR3FBInit(DDR3Addr):
    def __init__(self, sys_clk_freq, bitslip, delay, sdram_dfii_base, ddrphy_base):
        DDR3Addr.__init__(self, sdram_dfii_base = sdram_dfii_base, ddrphy_base = ddrphy_base)
        WishboneMaster.__init__(self,
            self.ddr3_init_instructions(sys_clk_freq) +
            self.ddr_config_instructions(bitslip, delay) +
            self.startfb() +
            [_DONE_CMD])

class DDR2Addr(DDR_Addr):
    def __init__(self, sdram_dfii_base, ddrphy_base):
        DDR_Addr.__init__(self, sdram_dfii_base = sdram_dfii_base, ddrphy_base = ddrphy_base)

    def ddr2_init_instructions(self, sys_clk_freq):
        return [
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            
            # phase
            _WRITE_CMD, self.ddrphy_rdphase, 1,
            _WRITE_CMD, self.ddrphy_wdphase, 0,
            
            # software control
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_reset_n | dfii_control_odt | dfii_control_cke,
            
            # reset
            _WRITE_CMD, self.ddrphy_rst, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            _WRITE_CMD, self.ddrphy_rst, 0,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.001),
            
            # bring cke high
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_cke|dfii_control_odt|dfii_control_reset_n,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.002),

	    # Precharge All
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x400,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # load extended mode register 3
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 3,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # load extended mode register 2
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 2,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # load extended mode register 1
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 1,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # load mode register / Reset DLL, CL=3, BL=4 
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x532,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.00002),

	    # Precharge All
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x400,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,

	    # Auto Refresh
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.0000004),

	    # Auto Refresh
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.0000004),
            
            # load mode register, CL=3, BL=4 
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x432,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 0,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            _WAIT_CMD | period_to_cycles(sys_clk_freq, 0.00002),

	    # Load Extended Mode Register / OCD Default
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x380,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 1,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,

	    # Load Extended Mode Register / OCD Exit
            _WRITE_CMD, self.sdram_dfii_pi0_address, 0x0,
            _WRITE_CMD, self.sdram_dfii_pi0_baddress, 1,
            _WRITE_CMD, self.sdram_dfii_pi0_command, dfii_command_ras|dfii_command_cas|dfii_command_we|dfii_command_cs,
            _WRITE_CMD, self.sdram_dfii_pi0_command_issue, 1,
            
            # hardware control
            _WRITE_CMD, self.sdram_dfii_control, dfii_control_sel,
        ]

class DDR2Init(DDR2Addr):
    def __init__(self, sys_clk_freq, bitslip, delay, sdram_dfii_base, ddrphy_base):
        DDR2Addr.__init__(self, sdram_dfii_base = sdram_dfii_base, ddrphy_base = ddrphy_base)
        WishboneMaster.__init__(self,
            self.ddr2_init_instructions(sys_clk_freq) +
            self.ddr_config_instructions(bitslip, delay) +
            self.startfb() +
            [_DONE_CMD])

