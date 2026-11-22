#
# Copyright (c) 2024 Romain Dolbeau <romain@dolbeau.org>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform
from litex.build.openocd import OpenOCD

# IOs ----------------------------------------------------------------------------------------------

# FPGA daughterboard I/O

_io = [
    ## 48 MHz clock reference
    ("clk100", 0, Pins("F4"), IOStandard("SSTL15")), # DDR_PLLCLK
    ## embedded 256 MiB DDR3 DRAM
    ("ddram", 0,
        Subsignal("a",
                  Pins("D3 B2 G1 D4 E1 D2 F1 D5 "
                       "C1 B3 E3 A1 E2 B4 C2 H1 "),
            IOStandard("SSTL15")),
        Subsignal("ba",    Pins("J4 F3 G2"), IOStandard("SSTL15")),
        Subsignal("ras_n", Pins("J2"), IOStandard("SSTL15")),
        Subsignal("cas_n", Pins("H6"), IOStandard("SSTL15")),
        Subsignal("we_n",  Pins("G4"), IOStandard("SSTL15")),
        Subsignal("cs_n",  Pins("H5"), IOStandard("SSTL15")), # not connected on Ztex, does that change init ?
        Subsignal("dm", Pins("E6"), IOStandard("SSTL15")),
        Subsignal("dq", Pins(
            "C5 B7 B6 C6 C7 D8 E5 E7"),
            IOStandard("SSTL15"),
            Misc("IN_TERM=UNTUNED_SPLIT_50")),
        Subsignal("dqs_p", Pins("A6"),
            IOStandard("DIFF_SSTL15"),
            Misc("IN_TERM=UNTUNED_SPLIT_50")),
        Subsignal("dqs_n", Pins("A5"),
            IOStandard("DIFF_SSTL15"),
            Misc("IN_TERM=UNTUNED_SPLIT_50")),
        Subsignal("clk_p", Pins("A4"), IOStandard("DIFF_SSTL15")),
        Subsignal("clk_n", Pins("A3"), IOStandard("DIFF_SSTL15")),
        Subsignal("cke",   Pins("H2"), IOStandard("SSTL15")),
        Subsignal("odt",   Pins("G6"), IOStandard("SSTL15")),
        Subsignal("reset_n", Pins("B1"), IOStandard("LVCMOS15")),
        Misc("SLEW=FAST"),
    ),
]

_flash_io_te0710 = [
    ("config_spiflash4x", 0,
        Subsignal("cs_n", Pins("L13")),
        # Subsignal("clk",  Pins("E9")), # 'E9' isn't a user pin, access clock via STARTUPE2 primitive, disabling the pads should do it in LiteSPIClkGen ?
        Subsignal("dq", Pins("K17 K18 L14 M14")),
        IOStandard("LVCMOS33"),
        Misc("SLEW=SLOW"),
        Misc("DRIVE=12"),
    ),
]

class TE0710Platform(XilinxPlatform):
    default_clk_name   = "clk100"
    default_clk_period = 1e9/100e6

    def __init__(self, variant="TE0710-03-42C21", version="V2.0", connectors=None):
        device = {
            "TE0710-03-42C21":  "xc7a35tcsg324-2", #untested
        }[variant]
        flash_io = {
            "TE0710-03-42C21":  _flash_io_te0710,
        }[variant]
        
        self.speedgrade = -1
        if (device[-1] == '2'):
            self.speedgrade = -2
        
        XilinxPlatform.__init__(self, device, _io, connectors, toolchain="vivado")
        
        self.add_extension(flash_io)
        
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_32BIT_ADDR YES [current_design]",
             "set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]",
             "set_property BITSTREAM.CONFIG.CONFIGRATE 66 [current_design]",
             "set_property BITSTREAM.GENERAL.COMPRESS true [current_design]",
             "set_property BITSTREAM.CONFIG.M1PIN PULLNONE [current_design]",
             "set_property BITSTREAM.CONFIG.M2PIN PULLNONE [current_design]",
             "set_property BITSTREAM.CONFIG.M0PIN PULLNONE [current_design]",
             "set_property BITSTREAM.CONFIG.USR_ACCESS TIMESTAMP [current_design]",
             #"set_property BITSTREAM.GENERAL.CRC DISABLE [current_design]",
             #"set_property STEPS.SYNTH_DESIGN.ARGS.RETIMING true [get_runs synth_1]",
             "set_property CONFIG_VOLTAGE 3.3 [current_design]",
             "set_property CFGBVS VCCO [current_design]"
#             , "set_property STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE AreaOptimized_high [get_runs synth_1]"
             ]

    def create_programmer(self):
        bscan_spi = "bscan_spi_xc7a35t.bit"
        return OpenOCD("openocd_xc7_ft2232.cfg", bscan_spi) #FIXME

    def do_finalize(self, fragment):
        XilinxPlatform.do_finalize(self, fragment)
        #self.add_period_constraint(self.lookup_request("clk48", loose=True), 1e9/48e6)
