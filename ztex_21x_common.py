#
# Copyright (c) 2015 Yann Sionneau <yann.sionneau@gmail.com>
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2020-2021 Romain Dolbeau <romain@dolbeau.org>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform
from litex.build.openocd import OpenOCD

# IOs ----------------------------------------------------------------------------------------------

# FPGA daughterboard I/O

_io = [
    ## 48 MHz clock reference
    ("clk48", 0, Pins("P15"), IOStandard("LVCMOS33")),
    ## embedded 256 MiB DDR3 DRAM
    ("ddram", 0,
        Subsignal("a", Pins("C5 B6 C7 D5 A3 E7 A4 C6", "A6 D8 B2 A5 B3 B7"),
            IOStandard("SSTL135")),
        Subsignal("ba",    Pins("E5 A1 E6"), IOStandard("SSTL135")),
        Subsignal("ras_n", Pins("E3"), IOStandard("SSTL135")),
        Subsignal("cas_n", Pins("D3"), IOStandard("SSTL135")),
        Subsignal("we_n",  Pins("D4"), IOStandard("SSTL135")),
#        Subsignal("cs_n",  Pins(""), IOStandard("SSTL135")),
        Subsignal("dm", Pins("G1 G6"), IOStandard("SSTL135")),
        Subsignal("dq", Pins(
            "H1 F1 E2 E1 F4 C1 F3 D2",
            "G4 H5 G3 H6 J2 J3 K1 K2"),
            IOStandard("SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_p", Pins("H2 J4"),
            IOStandard("DIFF_SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_n", Pins("G2 H4"),
            IOStandard("DIFF_SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("clk_p", Pins("C4"), IOStandard("DIFF_SSTL135")),
        Subsignal("clk_n", Pins("B4"), IOStandard("DIFF_SSTL135")),
        Subsignal("cke",   Pins("B1"), IOStandard("SSTL135")),
        Subsignal("odt",   Pins("F5"), IOStandard("SSTL135")),
        Subsignal("reset_n", Pins("J5"), IOStandard("SSTL135")),
        Misc("SLEW=FAST"),
    ),
]

_flash_io_2_13 = [
    ("config_spiflash", 0,
        Subsignal("cs_n", Pins("L13")),
        # Subsignal("clk",  Pins("E9")), # 'E9' isn't a user pin, access clock via STARTUPE2 primitive, disabling the pads should do it in LiteSPIClkGen ?
        Subsignal("mosi", Pins("K17")),
        Subsignal("miso", Pins("K18")),
        IOStandard("LVCMOS33"),
    ),
]
_flash_io_2_12 = [
    ("config_spiflash", 0,
        Subsignal("cs_n", Pins("L13")),
        # Subsignal("clk",  Pins("E9")), # 'E9' isn't a user pin, access clock via STARTUPE2 primitive, disabling the pads should do it in LiteSPIClkGen ?
        Subsignal("mosi", Pins("K17")),
        Subsignal("miso", Pins("K18")),
        IOStandard("LVCMOS33"),
    ),
    ("fx2_sloe", 0, Pins("T14"), IOStandard("LVCMOS33")),
]

class ZTexPlatform(XilinxPlatform):
    default_clk_name   = "clk48"
    default_clk_period = 1e9/48e6

    def __init__(self, variant="ztex2.13a", version="V1.0", connectors=None):
        device = {
            "ztex2.12a":  "xc7a15tcsg324-1", #untested, too small?
            "ztex2.12b":  "xc7a35tcsg324-1",
            "ztex2.13a":  "xc7a35tcsg324-1",
            "ztex2.13b":  "xc7a50tcsg324-1", #untested
            "ztex2.13b2": "xc7a50tcsg324-1", #untested
            "ztex2.13c":  "xc7a75tcsg324-2", #untested
            "ztex2.13d":  "xc7a100tcsg324-2" #untested
        }[variant]
        flash_io = {
            "ztex2.12a":  _flash_io_2_12,
            "ztex2.12b":  _flash_io_2_12,
            "ztex2.13a":  _flash_io_2_13,
            "ztex2.13b":  _flash_io_2_13,
            "ztex2.13b2": _flash_io_2_13,
            "ztex2.13c":  _flash_io_2_13,
            "ztex2.13d":  _flash_io_2_13,
        }[variant]
        
        self.speedgrade = -1
        if (device[-1] == '2'):
            self.speedgrade = -2
        
        XilinxPlatform.__init__(self, device, _io, connectors, toolchain="vivado")
        
        self.add_extension(flash_io)
        
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_32BIT_ADDR No [current_design]",
             "set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 2 [current_design]",
             "set_property BITSTREAM.CONFIG.CONFIGRATE 66 [current_design]",
             "set_property BITSTREAM.GENERAL.COMPRESS true [current_design]",
             "set_property BITSTREAM.GENERAL.CRC DISABLE [current_design]",
             "set_property STEPS.SYNTH_DESIGN.ARGS.RETIMING true [get_runs synth_1]",
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
