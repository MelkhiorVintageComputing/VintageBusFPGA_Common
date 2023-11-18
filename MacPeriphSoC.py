import os
from migen import *
from migen.genlib.fifo import *
from migen.fhdl.specials import Tristate

import litex
from litex.build.generic_platform import *
from litex.soc.integration.soc import *
from litex.soc.integration.soc_core import *

from litedram.modules import MT41J128M16
from litedram.phy import s7ddrphy

from litex.soc.cores.video import VideoS7HDMIPHY
from litex.soc.cores.video import VideoVGAPHY
from litex.soc.cores.video import video_timings
from VintageBusFPGA_Common.goblin_accel import *
        
class MacPeriphSoC(SoCCore):
    # Add SDCard -----------------------------------------------------------------------------------
    # WiP
    def add_sdcard_custom(self, name="sdcard", mode="read+write"):
        # Imports.
        from litesdcard.phy import SDPHY
        from litesdcard.core import SDCore

        # Checks.
        assert mode in ["read", "write", "read+write"]

        # Pads.
        sdcard_pads = self.platform.request(name)

        # Core.
        self.check_if_exists("sdphy")
        self.check_if_exists("sdcore")
        self.sdphy  = SDPHY(sdcard_pads, self.platform.device, self.clk_freq, cmd_timeout=10e-1, data_timeout=10e-1)
        self.sdcore = SDCore(self.sdphy)

    def __init__(self,
                 platform,
                 sys_clk_freq, 
                 csr_paging=0x800, #  default is 0x800
                 bus_interconnect = "crossbar",
                 goblin = False, hdmi = False, goblin_res = "1920x1080@60", use_goblin_alt = True,
                 **kwargs):
        print(f"Building MacPeriphSoC")
        
        kwargs["cpu_type"] = "None"
        kwargs["integrated_sram_size"] = 0
        kwargs["with_uart"] = False
        kwargs["with_timer"] = False
        
        self.sys_clk_freq = sys_clk_freq

        SoCCore.__init__(self,
                         platform = platform,
                         sys_clk_freq = sys_clk_freq,
                         clk_freq = sys_clk_freq,
                         csr_paging = csr_paging, #  default is 0x800
                         bus_interconnect = bus_interconnect,
                         **kwargs)
        
        if ((not use_goblin_alt) or (not hdmi)):
            from VintageBusFPGA_Common.goblin_fb import goblin_rounded_size, Goblin
        else:
            from VintageBusFPGA_Common.goblin_alt_fb import goblin_rounded_size, GoblinAlt
        
        if (goblin):
            hres = int(goblin_res.split("@")[0].split("x")[0])
            vres = int(goblin_res.split("@")[0].split("x")[1])
            self.goblin_fb_size = goblin_fb_size = goblin_rounded_size(hres, vres)
            print(f"Reserving {goblin_fb_size} bytes ({goblin_fb_size//1048576} MiB) for the goblin")
        else:
            hres = 0
            vres = 0
            self.goblin_fb_size = goblin_fb_size = 0
            # litex.soc.cores.video.video_timings.update(goblin_timings)
        
        # Quoting the doc:
        # * Separate address spaces are reserved for processor access to cards in NuBus slots. For a
        # * device in NuBus slot number s, the address space in 32-bit mode begins at address
        # * $Fs00 0000 and continues through the highest address, $FsFF FFFF (where s is a constant in
        # * the range $9 through $E for the Macintosh II, the Macintosh IIx, and the Macintosh IIfx;
        # * $A through $E for the Macintosh Quadra 900; $9 through $B for the Macintosh IIcx;
        # * $C through $E for the Macintosh IIci; $D and $E for the Macintosh Quadra 700; and
        # * $9 for the Macintosh IIsi).
        # the Q650 is $C through $E like the IIci, $E is the one with the PDS.
        # So at best we get 16 MiB in 32-bits mode, unless using "super slot space"
        # in 24 bits it's only one megabyte,  $s0 0000 through $sF FFFF
        # they are translated: '$s0 0000-$sF FFFF' to '$Fs00 0000-$Fs0F FFFF' (for s in range $9 through $E)
        # let's assume we have 32-bits mode, this can be requested in the DeclROM apparently
        self.wb_mem_map = wb_mem_map = {
            # master to map the NuBus access to RAM
            "master":            0x00000000, # to 0x3FFFFFFF
            "main_ram":          0x80000000, # not directly reachable from NuBus
            "video_framebuffer": 0x80000000 + 0x10000000 - goblin_fb_size, # Updated later
            # map everything in slot 0, remapped from the real slot in NuBus2Wishbone
            "goblin_mem":        0xF0000000, # up to 8 MiB of FB memory
            #"END OF FIRST MB" :  0xF00FFFFF,
            #"END OF 8 MB":       0xF07FFFFF,
            "goblin_bt" :        0xF0900000, # BT for goblin (regs)
            "goblin_accel" :     0xF0901000, # accel for goblin (regs)
            "goblin_accel_ram" : 0xF0902000, # accel for goblin (scratch ram)
            "stat"             : 0xF0903000, # stat
            "goblin_accel_rom" : 0xF0910000, # accel for goblin (rom)
            "goblin_audio_ram" : 0xF0920000, # audio for goblin (RAM buffers)
            "csr" :              0xF0A00000, # CSR
            "pingmaster":        0xF0B00000,
            "ethmac":            0xF0C00000,
            #"spiflash":         0xF0D00000, # testing
            #"config_spiflash":   0xF0D00000, # testing
            "rom":               0xF0FF8000, # ROM at the end (32 KiB of it ATM)
            "spiflash":          0xF0FF8000, # FIXME currently the flash is in the ROM spot, limited to 32 KiB
            "config_spiflash":   0xF0FF8000, # FIXME currently the flash is in the ROM spot, limited to 32 KiB
            #"END OF SLOT SPACE": 0xF0FFFFFF,
        }

    def mac_add_declrom(self, version, flash, config_flash):
        if ((not flash) and (not config_flash)): # so ROM is builtin
            rom_file = "rom_{}.bin".format(version.replace(".", "_"))
            rom_data = get_mem_data(filename_or_regions=rom_file, endianness="little") # "big"
            self.add_ram("rom", origin=self.mem_map["rom"], size=2**15, contents=rom_data, mode="r") ## 32 KiB, must match mmap
            print("$$$$$ ROM must be pre-existing for integration in the bitstream, double-check the ROM file is current for this configuration $$$$$\n");

        if (flash):
            from litespi.modules.generated_modules import W25Q128JV
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(mode="4x",
                               clk_freq = self.sys_clk_freq/4, # Fixme; PHY freq ?
                               module=W25Q128JV(Codes.READ_1_1_4),
                               region_size = 0x00008000, # 32 KiB
                               with_mmap=True, with_master=False)
            print("$$$$$ ROM must be put in the external Flash NOR $$$$$\n");

            
        if (config_flash):
            sector = 40
            from litespi.modules.generated_modules import S25FL128S
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(name="config_spiflash",
                               mode="1x",
                               clk_freq = self.sys_clk_freq/4, # Fixme; PHY freq ?
                               module=S25FL128S(Codes.READ_1_1_1),
                               region_size = 0x00008000, # 32 KiB,
                               region_offset = (sector * 65536),
                               with_mmap=True, with_master=False)
            try:
                # get and set the signal if we're on 2.12
                fx2_sloe = platform.request("fx2_sloe", 0)
                self.comb += [ fx2_sloe.eq(1), ] # force the FX2 side of the GPIF/FIFO interface to read, so we can access the flash
            except:
                # if the signal is not defined, we're on a 2.13 and don't need it
                self.comb += [ ]
                # ignore
            print(f"$$$$$ ROM must be put in the config Flash at sector {sector} $$$$$\n");
        
    def mac_add_sdram(self, hwinit = False, sdram_dfii_base = None, ddrphy_base = None):
        self.submodules.ddrphy = s7ddrphy.A7DDRPHY(self.platform.request("ddram"),
                                                   memtype        = "DDR3",
                                                   nphases        = 4,
                                                   sys_clk_freq   = self.sys_clk_freq)
        self.add_sdram("sdram",
                       phy           = self.ddrphy,
                       module        = MT41J128M16(self.sys_clk_freq, "1:4"),
                       l2_cache_size = 0,
        )
        self.avail_sdram = self.bus.regions["main_ram"].size

        if (hwinit):
            from VintageBusFPGA_Common.sdram_init import DDR3FBInit
            self.submodules.sdram_init = DDR3FBInit(sys_clk_freq = self.sys_clk_freq,
                                                    bitslip = 1, delay = 25, # CHECKME / FIXME: parameters
                                                    sdram_dfii_base = sdram_dfii_base, ddrphy_base = ddrphy_base)
            self.bus.add_master(name="DDR3Init", master=self.sdram_init.bus)

    def mac_add_goblin_prelim(self):
        base_fb = self.wb_mem_map["main_ram"] + self.avail_sdram - 1048576 # placeholder
        
        if (self.avail_sdram >= self.goblin_fb_size):
            self.avail_sdram = self.avail_sdram - self.goblin_fb_size
            base_fb = self.wb_mem_map["main_ram"] + self.avail_sdram
            self.wb_mem_map["video_framebuffer"] = base_fb
            print(f"FrameBuffer base_fb @ {base_fb:x}")
        else:
            print("***** ERROR ***** Can't have a FrameBuffer without main ram\n")
            assert(False)

    def mac_add_goblin(self, use_goblin_alt = True, hdmi = True, goblin_res = None, goblin_irq = None, audio_irq = None):
        
        if ((not use_goblin_alt) or (not hdmi)):
            from VintageBusFPGA_Common.goblin_fb import goblin_rounded_size, Goblin
        else:
            from VintageBusFPGA_Common.goblin_alt_fb import goblin_rounded_size, GoblinAlt
                
        if (not hdmi):
            self.submodules.videophy = VideoVGAPHY(platform.request("vga"), clock_domain="vga")
            self.submodules.goblin = Goblin(soc=self, phy=self.videophy, timings=goblin_res, clock_domain="vga", irq_line=goblin_irq, endian="little", hwcursor=False, truecolor=True) # clock_domain for the VGA side, goblin is running in cd_sys
        else:
            if (not use_goblin_alt):
                self.submodules.videophy = VideoS7HDMIPHY(platform.request("hdmi"), clock_domain="hdmi")
                self.submodules.goblin = Goblin(soc=self, phy=self.videophy, timings=goblin_res, clock_domain="hdmi", irq_line=goblin_irq, endian="little", hwcursor=False, truecolor=True) # clock_domain for the HDMI side, goblin is running in cd_sys
            else:
                # GoblinAlt contains its own PHY
                self.submodules.goblin = GoblinAlt(soc=self, timings=goblin_res, clock_domain="hdmi", irq_line=goblin_irq, endian="little", hwcursor=False, truecolor=True)
                # it also has a bus master so that the audio bit can fetch data from Wishbone
                self.bus.add_master(name="GoblinAudio", master=self.goblin.goblin_audio.busmaster)
                self.add_ram("goblin_audio_ram", origin=self.mem_map["goblin_audio_ram"], size=2**13, mode="rw") # 8 KiB buffer, planned as 2*4KiB
                self.comb += [ audio_irq.eq(self.goblin.goblin_audio.irq), ]
                    
        self.bus.add_slave("goblin_bt", self.goblin.bus, SoCRegion(origin=self.mem_map.get("goblin_bt", None), size=0x1000, cached=False))
        #pad_user_led_0 = platform.request("user_led", 0)
        #pad_user_led_1 = platform.request("user_led", 1)
        #self.comb += pad_user_led_0.eq(self.goblin.video_framebuffer.underflow)
        #self.comb += pad_user_led_1.eq(self.goblin.video_framebuffer.fb_dma.enable)
        if (True):
            self.submodules.goblin_accel = GoblinAccelNuBus(soc = self)
            self.bus.add_slave("goblin_accel", self.goblin_accel.bus, SoCRegion(origin=self.mem_map.get("goblin_accel", None), size=0x1000, cached=False))
            self.bus.add_master(name="goblin_accel_r5_i", master=self.goblin_accel.ibus)
            self.bus.add_master(name="goblin_accel_r5_d", master=self.goblin_accel.dbus)
            goblin_rom_file = "VintageBusFPGA_Common/blit_goblin_nubus.raw"
            goblin_rom_data = get_mem_data(filename_or_regions=goblin_rom_file, endianness="little")
            goblin_rom_len = 4*len(goblin_rom_data);
            rounded_goblin_rom_len = 2**log2_int(goblin_rom_len, False)
            print(f"GOBLIN ROM is {goblin_rom_len} bytes, using {rounded_goblin_rom_len}")
            assert(rounded_goblin_rom_len <= 2**16)
            self.add_ram("goblin_accel_rom", origin=self.mem_map["goblin_accel_rom"], size=rounded_goblin_rom_len, contents=goblin_rom_data, mode="r")
            self.add_ram("goblin_accel_ram", origin=self.mem_map["goblin_accel_ram"], size=2**12, mode="rw")
        
