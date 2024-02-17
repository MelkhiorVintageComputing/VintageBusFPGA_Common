from migen import *
from migen.genlib.fifo import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream
from litex.soc.interconnect import wishbone
from litex.soc.cores.code_tmds import TMDSEncoder

from litex.build.io import SDROutput, DDROutput

from migen.genlib.cdc import MultiReg

from litex.soc.cores.video import *

from VintageBusFPGA_Common.fb_video import *
from VintageBusFPGA_Common.fb_dma import LiteDRAMFBDMAReader

from VintageBusFPGA_Common.goblin_alt_audio import GoblinAudio

from math import ceil

cmap_layout = [
    ("color", 2),
    ("address", 8),
    ("data", 8),
]
omap_layout = [
    ("color", 2),
    ("address", 2),
    ("data", 8),
]

def goblin_rounded_size(hres, vres, bus="NuBus"):
    mib = int(ceil(((hres * vres) + 0) / 1048576))
    if (mib > 0 and mib < 8 and (bus == "NuBus")): # FIXME : NuBus
        mib = 8
    if (mib > 0 and mib < 16 and (bus == "SBus")): # FIXME : SBus
        mib = 16
    if (mib > 16 or mib < 1):
        print(f"{mib} mebibytes framebuffer not supported")
        assert(False)
    return int(1048576 * mib)

class VideoFrameBufferMultiDepth(Module, AutoCSR):
    """Video FrameBufferMultiDepth"""
    def __init__(self, dram_port, upd_clut_fifo = None, hres=800, vres=600, base=0x00000000, fifo_depth=65536, clock_domain="sys", clock_faster_than_sys=False, hwcursor=False, upd_overlay_fifo=False, upd_omap_fifo=False, truecolor=True, endian="big"):
        
        print(f"FRAMEBUFFER: dram_port.data_width = {dram_port.data_width}, {hres}x{vres}, 0x{base:x}, in {clock_domain}, clock_faster_than_sys={clock_faster_than_sys}")
        
        vga_sync = getattr(self.sync, clock_domain) # usually should be named hdmi_sync, really...

        # if 0, 32-bits mode
        # should only be changed while in reset
        self.use_indexed = Signal(1, reset = 0x1)
        # mode, as x in 2^x (so 1, 2, 4, 8 bits)
        # should only be changed while in reset
        self.indexed_mode = Signal(2, reset = 0x3)
        # for the VBL interrupt
        self.vblping = Signal(reset = 0)

        # vtg_sink replacement
        self.de = Signal() # are we in windowed picture ?
        self.inframe = Signal() # are we in the frame (native resolution here, not the same as the HDMI frame...) ? # probably not needed, only used for underflow - we need underflow during reset, but it could/should be based on 'de' instead
        self.last = Signal() # end-of-picture marker
        if (hwcursor):
            self.hwcursor = Signal()
            self.hwcursorx = Signal(5)
            self.hwcursory = Signal(5)
        
        if (hwcursor):
            upd_omap_fifo_dout = Record(omap_layout)
            self.comb += upd_omap_fifo_dout.raw_bits().eq(upd_omap_fifo.dout)
            overlay = Array(Array(Array(Signal(1) for x in range(0,32)) for y in range(0,32)) for i in range(0, 2))
            omap = Array(Array(Signal(8, reset = (255-i)) for i in range(0, 4)) for j in range(0, 3))
            vga_sync += [
                If(upd_overlay_fifo.readable,
                    upd_overlay_fifo.re.eq(1),
                    [ overlay[upd_overlay_fifo.dout[0]][upd_overlay_fifo.dout[1:6]][x].eq(upd_overlay_fifo.dout[6+x]) for x in range(0, 32)],
                    ).Else(
                        upd_overlay_fifo.re.eq(0),
                    )
            ]
            vga_sync += [
                If(upd_omap_fifo.readable,
                   upd_omap_fifo.re.eq(1),
                   omap[upd_omap_fifo_dout.color][upd_omap_fifo_dout.address].eq(upd_omap_fifo_dout.data),
                ).Else(
                    upd_omap_fifo.re.eq(0),
                )
            ]
        #else:


        
        self.source    = source   = stream.Endpoint(video_data_layout)
        self.underflow = Signal()

        #source_buf_ready = Signal()
        source_buf_valid = Signal()
        source_buf_de = Signal()
        source_buf_inframe = Signal()
        data_buf_index = Signal(8)
        data_buf_direct = Array(Signal(8) for x in range(3))
        if (hwcursor):
            hwcursor_buf = Signal()
            hwcursorx_buf = Signal(5)
            hwcursory_buf = Signal(5)
        
        source_buf_b_valid = Signal()
        source_buf_b_de = Signal()
        source_buf_b_inframe = Signal()
        data_buf_b_index = Signal(8)
        if (truecolor):
            data_buf_b_direct = Array(Signal(8) for x in range(3))
        if (hwcursor):
            hwcursor_color_idx = Signal(2)
        
        #source_out_ready = Signal()
        source_out_valid = Signal()
        source_out_de = Signal()
        source_out_inframe = Signal()
        source_out_r = Signal(8)
        source_out_g = Signal(8)
        source_out_b = Signal(8)
        
        # # #
        # First the Color Look-up Table (for all but 1 bit & 16/32 bits)
        # updated from the FIFO
        # 8-and-less-than-8-bits mode used the 2^x first entries
        ### clut = Array(Array(Signal(8, reset = (255-i)) for i in range(0, 256)) for j in range(0, 3))
        clut = Array(Array(Signal(8, reset = (255-i)) for j in range(0, 3)) for i in range(0, 256))
        
        upd_clut_fifo_dout = Record(cmap_layout)
        self.comb += upd_clut_fifo_dout.raw_bits().eq(upd_clut_fifo.dout)
        vga_sync += [
                     If(upd_clut_fifo.readable,
                        upd_clut_fifo.re.eq(1),
                        clut[upd_clut_fifo_dout.address][upd_clut_fifo_dout.color].eq(upd_clut_fifo_dout.data),
                        ).Else(
                               upd_clut_fifo.re.eq(0),
                               )
                     ]

        # # #

        # Video DMA.
        # length should be changed to match mode
        self.submodules.fb_dma = LiteDRAMFBDMAReader(dram_port,
                                                     fifo_depth     = fifo_depth//(dram_port.data_width//8),
                                                     default_base   = base,
                                                     default_length = (hres * vres)) # default to max
        
        # If DRAM Data Width > 8-bit and Video clock is faster than sys_clk:
        # actually always use that case to simplify the design
        # if (dram_port.data_width > 8) and clock_faster_than_sys:
        # Do Clock Domain Crossing first...
        self.submodules.cdc = stream.ClockDomainCrossing([("data", dram_port.data_width)], cd_from="sys", cd_to=clock_domain)
        self.comb += self.fb_dma.source.connect(self.cdc.sink)
        # ... and then Data-Width Conversion.
        # we have 5 possible conversion and mux/connect the appropriate one
        if (truecolor):
            self.submodules.conv32 = ClockDomainsRenamer({"sys": clock_domain})(stream.Converter(dram_port.data_width, 32))
            self.submodules.conv16 = ClockDomainsRenamer({"sys": clock_domain})(stream.Converter(dram_port.data_width, 16))
                
            handle_truecolor_sink = [ Case(self.indexed_mode, {
                0x0: [ self.cdc.source.connect(self.conv32.sink) ],
                0x1: [ self.cdc.source.connect(self.conv16.sink) ],
            })]
                
            handle_truecolor_source = [ Case(self.indexed_mode, {
                0x0: [ source_buf_valid.eq(self.conv32.source.valid), self.conv32.source.connect(source, keep={"ready"}), ],
                0x1: [ source_buf_valid.eq(self.conv16.source.valid), self.conv16.source.connect(source, keep={"ready"}), ],
            })]
            
            if (endian == "big"): # this starts to _really_ mean "i'm in the SBusFPGA"...
                handle_truecolor_databuf = [ Case(self.indexed_mode, {
                    0x0: [ data_buf_direct[2].eq(self.conv32.source.data[24:32]),
                           data_buf_direct[1].eq(self.conv32.source.data[16:24]),
                           data_buf_direct[0].eq(self.conv32.source.data[8:16]), ],
                    0x1: [ data_buf_direct[0].eq(Cat(Signal(3, reset = 0), self.conv16.source.data[0:5])), # fixme: 16-bits in X11 ??? (this is QD32)
                           data_buf_direct[1].eq(Cat(Signal(3, reset = 0), self.conv16.source.data[5:10])),
                           data_buf_direct[2].eq(Cat(Signal(3, reset = 0), self.conv16.source.data[10:15])), ]
                })]
            else: # and little "i'm in the NuBusFPGA" ...
                handle_truecolor_databuf =[ Case(self.indexed_mode, {
                    0x0: [ data_buf_direct[2].eq(self.conv32.source.data[24:32]),
                           data_buf_direct[1].eq(self.conv32.source.data[16:24]),
                           data_buf_direct[0].eq(self.conv32.source.data[8:16]), ],
                    0x1: [ data_buf_direct[0].eq(Cat(self.conv16.source.data[ 4: 7], self.conv16.source.data[ 2: 7])), # 16-bits in QD32
                           data_buf_direct[1].eq(Cat(self.conv16.source.data[15:16], self.conv16.source.data[ 0: 2],   # seems byte-swapped in 5551 BGRx
                                                     self.conv16.source.data[13:16], self.conv16.source.data[ 0: 2])),
                           data_buf_direct[2].eq(Cat(self.conv16.source.data[10:13], self.conv16.source.data[ 8:13])), ]
                })]
                
            handle_truecolor_databuf_b = [ data_buf_b_direct[0].eq(data_buf_direct[0]),
                                           data_buf_b_direct[1].eq(data_buf_direct[1]),
                                           data_buf_b_direct[2].eq(data_buf_direct[2]), ]
            handle_truecolor_final_source = [ source_out_r.eq(data_buf_b_direct[2]),
                                              source_out_g.eq(data_buf_b_direct[1]),
                                              source_out_b.eq(data_buf_b_direct[0]), ]
            
        else:
            handle_truecolor_sink = [ ]
            handle_truecolor_source = [ ]
            handle_truecolor_databuf = [ ]
            handle_truecolor_databuf_b = [ ]
            handle_truecolor_final_source = [ ]
        self.submodules.conv8 = ClockDomainsRenamer({"sys": clock_domain})(stream.Converter(dram_port.data_width, 8))
        self.submodules.conv4 = ClockDomainsRenamer({"sys": clock_domain})(stream.Converter(dram_port.data_width, 4))
        self.submodules.conv2 = ClockDomainsRenamer({"sys": clock_domain})(stream.Converter(dram_port.data_width, 2))
        self.submodules.conv1 = ClockDomainsRenamer({"sys": clock_domain})(stream.Converter(dram_port.data_width, 1))

        # not sure the bit-reversal needed in the NuBusFPGA is really tied to the endianess (didn't really try < 8 bits on SBusFPGA)
        if (endian == "big"):
            self.comb += [
                If(self.use_indexed,
                   Case(self.indexed_mode, {
                       0x3: [ self.cdc.source.connect(self.conv8.sink), ],
                       0x2: [ self.cdc.source.connect(self.conv4.sink), ],
                       0x1: [ self.cdc.source.connect(self.conv2.sink), ],
                       0x0: [ self.cdc.source.connect(self.conv1.sink), ],
                   })
                ).Else(
                    *handle_truecolor_sink
                )
            ]
        else:
            self.comb += [
                If(self.use_indexed,
                   Case(self.indexed_mode, {
                       0x3: [ self.cdc.source.connect(self.conv8.sink), ],
                       0x2: [ self.cdc.source.connect(self.conv4.sink, omit={"data"}),
                              *[ self.conv4.sink.data[xbyte*8 + xbit*4:xbyte*8 + xbit*4+4].eq(self.cdc.source.data[xbyte*8 + 4-xbit*4:xbyte*8 + 4-xbit*2+4]) for xbit in range(0,2) for xbyte in range(0, dram_port.data_width//8) ], ],
                       0x1: [ self.cdc.source.connect(self.conv2.sink, omit={"data"}),
                              *[ self.conv2.sink.data[xbyte*8 + xbit*2:xbyte*8 + xbit*2+2].eq(self.cdc.source.data[xbyte*8 + 6-xbit*2:xbyte*8 + 6-xbit*2+2]) for xbit in range(0,4) for xbyte in range(0, dram_port.data_width//8) ], ],
                       0x0: [ self.cdc.source.connect(self.conv1.sink, omit={"data"}),
                              *[ self.conv1.sink.data[xbyte*8 + xbit].eq(self.cdc.source.data[xbyte*8 + 7-xbit]) for xbit in range(0,8) for xbyte in range(0, dram_port.data_width//8) ],
                       ],
                   })
                ).Else(
                    *handle_truecolor_sink
                )
            ]
            
        
            
        # Video Generation.
        self.comb += [
            If(self.de, # 1 cycle after cx/cy
               If(self.use_indexed,
                  Case(self.indexed_mode, {
                      0x3: [ source_buf_valid.eq(self.conv8.source.valid),
                             self.conv8.source.connect(source, keep={"ready"}),
                      ],
                      0x2: [ source_buf_valid.eq(self.conv4.source.valid),
                             self.conv4.source.connect(source, keep={"ready"}),
                      ],
                      0x1: [ source_buf_valid.eq(self.conv2.source.valid),
                             self.conv2.source.connect(source, keep={"ready"}),
                      ],
                      0x0: [ source_buf_valid.eq(self.conv1.source.valid),
                             self.conv1.source.connect(source, keep={"ready"}),
                      ],
                  }),
               ).Else(
                   *handle_truecolor_source,
               ),
            ),
            source_buf_de.eq(self.de),
            source_buf_inframe.eq(self.inframe),
            Case(self.indexed_mode, {
                0x3: [ data_buf_index.eq(self.conv8.source.data),
                ],
                0x2: [ data_buf_index.eq(Cat(self.conv4.source.data, Signal(4, reset = 0))),
                ],
                0x1: [ data_buf_index.eq(Cat(self.conv2.source.data, Signal(6, reset = 0))),
                ],
                0x0: [ data_buf_index.eq(Replicate(self.conv1.source.data, 8)),
                ],
            }),
            *handle_truecolor_databuf,
        ]
        if (hwcursor):
            self.comb += [
                hwcursor_buf.eq(self.hwcursor),
                hwcursorx_buf.eq(self.hwcursorx),
                hwcursory_buf.eq(self.hwcursory),
            ]
        
        vga_sync += [
            source_buf_b_de.eq(source_buf_de), # 2 cycles after cx/cy
            source_buf_b_inframe.eq(source_buf_inframe),
            source_buf_b_valid.eq(source_buf_valid),
            data_buf_b_index.eq(data_buf_index),
            *handle_truecolor_databuf_b,
        ]
        if (hwcursor):
            vga_sync += [
                If(hwcursor_buf,
                   hwcursor_color_idx.eq(Cat(overlay[0][hwcursory_buf][hwcursorx_buf], overlay[1][hwcursory_buf][hwcursorx_buf])),
                ).Else(
                    hwcursor_color_idx.eq(0),
                )
            ]
            
        vga_sync += [
            source_out_de.eq(source_buf_b_de), # 3 cycles after cx/cy
            source_out_inframe.eq(source_buf_b_inframe),
            source_out_valid.eq(source_buf_b_valid),
            #source_buf_ready.eq(source_out_ready), # ready flow the other way
        ]
        if (hwcursor):
            vga_sync += [
                If(hwcursor_color_idx != 0,
                   source_out_r.eq(omap[0][hwcursor_color_idx]),
                   source_out_g.eq(omap[1][hwcursor_color_idx]),
                   source_out_b.eq(omap[2][hwcursor_color_idx]),
                ).Elif(source_buf_b_de, # also 3 cycles after cx/cy
                       If(self.use_indexed,
                          source_out_r.eq(clut[data_buf_b_index][2]),
                          source_out_g.eq(clut[data_buf_b_index][1]),
                          source_out_b.eq(clut[data_buf_b_index][0])
                       ).Else(
                           *handle_truecolor_final_source,
                       ),
                ).Else(source_out_r.eq(0),
                       source_out_g.eq(0),
                       source_out_b.eq(0)
                )
            ]
        else:
            vga_sync += [
                If(source_buf_b_de, # also 3 cycles after cx/cy
                       If(self.use_indexed,
                          source_out_r.eq(clut[data_buf_b_index][2]),
                          source_out_g.eq(clut[data_buf_b_index][1]),
                          source_out_b.eq(clut[data_buf_b_index][0])
                       ).Else(
                           *handle_truecolor_final_source,
                       ),
                ).Else(source_out_r.eq(0),
                       source_out_g.eq(0),
                       source_out_b.eq(0)
                )
            ]
            
        self.comb += [
            source.de.eq(source_out_inframe), # inframe, not de
            source.valid.eq(source_out_valid),
            source.r.eq(source_out_b), # something got swapped at some point...
            source.g.eq(source_out_g),
            source.b.eq(source_out_r),
        ]

        # Underflow.
        self.comb += self.underflow.eq(~source.valid & source.de)
        
        # VBL handling
        # create a pulse in self.vlbping in sys at the end of the frame
        from migen.genlib.cdc import PulseSynchronizer
        old_last = Signal()
        vga_vblping = Signal()
        vga_sync += [
                     old_last.eq(self.last),
                     If((self.last == 1) & (old_last == 0),
                        vga_vblping.eq(1),
                        ).Else(
                               vga_vblping.eq(0)
                               )
                     ]
        self.submodules.vbl_ps = PulseSynchronizer(idomain = clock_domain, odomain = "sys")
        self.comb += self.vbl_ps.i.eq(vga_vblping)
        self.comb += self.vblping.eq(self.vbl_ps.o)

class GoblinAlt(Module, AutoCSR):
    def __init__(self, soc=None, timings=None, clock_domain="sys", irq_line=None, endian="big", hwcursor=True, truecolor=True):
        platform = soc.platform

        self.add_sources(platform)
        
        # 2 bits for color (0/r, 1/g, 2/b), 8 for @ and 8 for value
        self.submodules.upd_cmap_fifo = upd_cmap_fifo = ClockDomainsRenamer({"read": clock_domain, "write": "sys"})(AsyncFIFOBuffered(width=layout_len(cmap_layout), depth=8))
        upd_cmap_fifo_din = Record(cmap_layout)
        self.comb += self.upd_cmap_fifo.din.eq(upd_cmap_fifo_din.raw_bits())

        # hw cursor support
        self.submodules.upd_overlay_fifo = upd_overlay_fifo = ClockDomainsRenamer({"read": clock_domain, "write": "sys"})(AsyncFIFOBuffered(width=1+5+32, depth=8))
        self.submodules.upd_omap_fifo = upd_omap_fifo = ClockDomainsRenamer({"read": clock_domain, "write": "sys"})(AsyncFIFOBuffered(width=layout_len(omap_layout), depth=8))
        upd_omap_fifo_din = Record(omap_layout)
        self.comb += self.upd_omap_fifo.din.eq(upd_omap_fifo_din.raw_bits())
        
        name = "video_framebuffer"
        # near duplicate of plaform.add_video_framebuffer
        # Video Timing Generator. Interface, we only keep the CSR & timings stuff for compatibility
        vtg = FBVideoTimingGeneratorInterface(default_video_timings=timings if isinstance(timings, str) else timings[1])
        vtg = ClockDomainsRenamer(clock_domain)(vtg)
        setattr(self.submodules, f"{name}_vtg", vtg)
        vtg_enable = Signal(reset = 0)
        self.comb += [ vtg.enable.eq(vtg_enable) ]

        # Video FrameBuffer.
        timings = timings if isinstance(timings, str) else timings[0]
        base = soc.mem_map.get(name)
        print(f"goblin: visible memory at {base:x}")
        hres = int(timings.split("@")[0].split("x")[0])
        vres = int(timings.split("@")[0].split("x")[1])
        assert(hres == vtg.video_timings["h_active"])
        assert(vres == vtg.video_timings["v_active"])
        freq = vtg.video_timings["pix_clk"]
        print(f"goblin: using {hres} x {vres}, {freq/1e6} MHz pixclk")
        vfb = VideoFrameBufferMultiDepth(dram_port = soc.sdram.crossbar.get_port(),
                                         upd_clut_fifo = upd_cmap_fifo,
                                         hres = hres,
                                         vres = vres,
                                         base = base,
                                         fifo_depth=(64*1024),
                                         clock_domain = clock_domain,
                                         clock_faster_than_sys = (vtg.video_timings["pix_clk"] > soc.sys_clk_freq),
                                         hwcursor = True,
                                         upd_overlay_fifo = upd_overlay_fifo,
                                         upd_omap_fifo = upd_omap_fifo,
                                         truecolor = truecolor,
                                         endian = endian,
        )
        setattr(self.submodules, name, vfb)

        # Connect Video FrameBuffer to Video PHY.
        #self.comb += vfb.source.connect(phy if isinstance(phy, stream.Endpoint) else phy.sink)

        # Constants.
        soc.add_constant("VIDEO_FRAMEBUFFER_BASE", base)
        soc.add_constant("VIDEO_FRAMEBUFFER_HRES", hres)
        soc.add_constant("VIDEO_FRAMEBUFFER_VRES", vres)

        # Wishbone
        self.bus = bus = wishbone.Interface()

        # HW Cursor

        if (hwcursor):
            hwcursor_x = Signal(12) # FIXME
            hwcursor_y = Signal(12) # FIXME
            # HW cursor lut in reg 0x20
            # HW cursor XY in reg 0x24
            handle_hwcursor = [ NextValue(hwcursor_x, bus.dat_w[16:28]), # FIXME: endianess
                                NextValue(hwcursor_y, bus.dat_w[ 0:12]), # FIXME: endianess
            ]
        else:
            handle_hwcursor = [ ]

        # current cmap logic for the goblin, similar to the cg6, minus the HW cursor
        bt_mode = Signal(8, reset = 0x3) # bit depth is 2^x ; 0x10 is direct mode (32 bits) # reg 0x0
        bt_addr = Signal(8, reset = 0) # reg 0x14 ; lut itself in reg 0x18
        bt_cmap_state = Signal(2, reset = 0) 
        m_vbl_disable = Signal(reset = 1) # reg 0x4
        bt_upd = Signal()

        # for sub-resolution
        hres_start = Signal(hbits, reset = 0)
        hres_end   = Signal(hbits, reset = hres)
        vres_start = Signal(vbits, reset = 0)
        vres_end   = Signal(vbits, reset = vres)
        vres_upd = Signal()

        videoctrl = Signal() # reg 0x8
        videoctrl_upd = Signal()
        videoctrl_busy = Signal()
        
        vbl_signal = Signal(reset = 0) # reg 0xC
        self.comb += irq_line.eq(~vbl_signal | m_vbl_disable) # irq_line is active low

        if (endian == "big"):
            low_byte = slice(0, 8)
            low_bit = slice(0, 1)
        else:
            low_byte = slice(24, 32)
            low_bit = slice(24, 25)
            
        self.submodules.wishbone_fsm = wishbone_fsm = FSM(reset_state = "Reset")
        wishbone_fsm.act("Reset",
                         NextValue(bus.ack, 0),
                         NextState("Idle"))
        wishbone_fsm.act("Idle",
                         If(bus.cyc & bus.stb & bus.we & ~bus.ack & upd_cmap_fifo.writable, #write
                            # FIXME: should check for prefix?
                            Case(bus.adr[0:18], {
                                "default": [],
                                # gobofb_mode
                                0x0: [ NextValue(bt_mode, bus.dat_w[low_byte]),
                                       NextValue(bt_upd, 1), ],
                                # set vbl
                                0x1: [ NextValue(m_vbl_disable, ~bus.dat_w[low_bit]), ],
                                # gobofb on/off
                                0x2: [ NextValue(videoctrl, bus.dat_w[low_bit]),
                                       NextValue(videoctrl_upd, 1), ],
                                # clear irq
                                0x3: [ NextValue(vbl_signal, 0), ],
                                # 0x4: reset in SW
                                # gobofb_lut_addr
                                0x5: [ NextValue(bt_addr, bus.dat_w[low_byte]),
                                       NextValue(bt_cmap_state, 0),
                                ],
                                # gobofb_lut
                                0x6: [ upd_cmap_fifo.we.eq(1),
                                           upd_cmap_fifo_din.color.eq(bt_cmap_state),
                                           upd_cmap_fifo_din.address.eq(bt_addr),
                                           upd_cmap_fifo_din.data.eq(bus.dat_w[low_byte]),
                                           Case(bt_cmap_state, {
                                               0: [ NextValue(bt_cmap_state, 1), ],
                                               1: [ NextValue(bt_cmap_state, 2), ],
                                               2: [ NextValue(bt_cmap_state, 0), NextValue(bt_addr, (bt_addr+1) & 0xFF), ],
                                               "default":  NextValue(bt_cmap_state, 0),
                                           }),
                                ],
                                # 0x7: debug in SW
                                # cursor lut
                                0x8: [ upd_omap_fifo.we.eq(1),
                                       upd_omap_fifo_din.color.eq(bt_cmap_state),
                                       upd_omap_fifo_din.address.eq(bt_addr[0:2]),
                                       upd_omap_fifo_din.data.eq(bus.dat_w[low_byte]),
                                       Case(bt_cmap_state, {
                                           0: [ NextValue(bt_cmap_state, 1), ],
                                           1: [ NextValue(bt_cmap_state, 2), ],
                                           2: [ NextValue(bt_cmap_state, 0), NextValue(bt_addr, (bt_addr+1) & 0xFF), ],
                                           "default":  NextValue(bt_cmap_state, 0),
                                       }),
                                ],
                                # hw cursor x/y
                                0x9: [ *handle_hwcursor ],
                                # resolution handling
                                # 0x10: hres (r/o)
                                # 0x11: vres (r/o)
                                0x12: [ NextValue(hres_start, bus.dat_w), ], # hres_start
                                0x13: [ NextValue(vres_start, bus.dat_w), ], # vres_start
                                0x14: [ NextValue(hres_end,   bus.dat_w), ], # hres_end
                                0x15: [ NextValue(vres_end,   bus.dat_w),
                                        NextValue(vres_upd, 1),
                                ], # vres_end
                            }),
                            Case(bus.adr[5:18], { # mask and bits in registers from 0x80 and 0x100
                                "default": [], # fixme: hwcursor for 0x1/0x2
                                0x1 : [ upd_overlay_fifo.we.eq(1), # 1*32 = 32..63 / 0x20..0x3F
                                        upd_overlay_fifo.din.eq(Cat(Signal(1, reset = 0), 31-bus.adr[0:5], bus.dat_w)) # FIXME: endianess
                                ],
                                0x2 : [ upd_overlay_fifo.we.eq(1), # 2*32 = 64..95 / 0x40..0x5F
                                        upd_overlay_fifo.din.eq(Cat(Signal(1, reset = 1), 31-bus.adr[0:5], bus.dat_w)) # FIXME: endianess
                                ],
                            }),
                            NextValue(bus.ack, 1),
                         ).Elif(bus.cyc & bus.stb & ~bus.we & ~bus.ack, #read
                                Case(bus.adr[0:18], {
                                    # bt_addr
                                    0x0: [ NextValue(bus.dat_r[low_byte], bt_mode), ],
                                    0x2: [ NextValue(bus.dat_r[low_byte], Cat(videoctrl, videoctrl_busy)), ],
                                    0x3: [ NextValue(bus.dat_r[low_byte], ~irq_line), ], # irq_line is active low
                                    "default": [ NextValue(bus.dat_r, 0xDEADBEEF)],
                                    0x10: [ NextValue(bus.dat_r, hres), ], # hres (r/o) # FIXME: endianess
                                    0x11: [ NextValue(bus.dat_r, vres), ], # vres (r/o) # FIXME: endianess
                                    0x12: [ NextValue(bus.dat_r, hres_start), ], # hres_start # FIXME: endianess
                                    0x13: [ NextValue(bus.dat_r, vres_start), ], # vres_start # FIXME: endianess
                                    0x14: [ NextValue(bus.dat_r, hres_end), ], # hres_end # FIXME: endianess
                                    0x15: [ NextValue(bus.dat_r, vres_end), ], # vres_end # FIXME: endianess
                                }),
                                NextValue(bus.ack, 1),
                         ).Else(
                             NextValue(bus.ack, 0),
                         ),
        )
        # mode switch logic
        #npixels = hres * vres
        npixels = Signal(hbits + vbits + 1, reset = (hres * vres))
        in_reset = Signal()
        post_reset_ctr = Signal(3)
        previous_videoctrl = Signal()

        hwidth  = Signal(hbits)
        vheight = Signal(vbits)
        self.sync += [
            hwidth.eq(hres_end - hres_start),
            vheight.eq(vres_end - vres_start),
            npixels.eq(hwidth * vheight),
        ]
        if (truecolor):
            handle_truecolor_bit = [ self.video_framebuffer.use_indexed.eq(~bt_mode[4:5]) ]
        else:
            handle_truecolor_bit = [ ]
        
        # this has grown complicated and should be a FSM...
        self.sync += [ If(bt_upd | vres_upd,
                          bt_upd.eq(0),
                          vres_upd.eq(0),
                          in_reset.eq(1),
                          post_reset_ctr.eq(0),
                          videoctrl.eq(0), # start a disabling cycle, or stay disabled
                          videoctrl_upd.eq(1), # start a disabling cycle, or stay disabled
                          previous_videoctrl.eq(videoctrl | previous_videoctrl), # preserve old state for restoration later, if 'previous' is already set then we just had an update in the middle of an update...
                       ),
                       If(~bt_upd & ~vres_upd & in_reset & ~vtg_enable, # we asked for a reset and by now, the VTG has been turned off (or was off)
                          self.video_framebuffer.indexed_mode.eq(bt_mode[0:2]),
                          *handle_truecolor_bit,
                          in_reset.eq(0),
                          post_reset_ctr.eq(7),
                          # reconfigure the VTG
                          vtg._hres_start.eq(hres_start),
                          vtg._hres_end.eq(  hres_end),
                          vtg._vres_start.eq(vres_start),
                          vtg._vres_end.eq(  vres_end),
                       ),
                       If(~bt_upd & ~vres_upd & (post_reset_ctr == 4), # now reconfigure the DMA
                          If(bt_mode[4:5],
                              Case(bt_mode[0:2], {
                                  0x0: self.video_framebuffer.fb_dma.length.eq(npixels << 2),
                                  0x1: self.video_framebuffer.fb_dma.length.eq(npixels << 1),
                              }),
                          ).Else(
                              Case(bt_mode[0:2], {
                                  3: self.video_framebuffer.fb_dma.length.eq(npixels     ),
                                  2: self.video_framebuffer.fb_dma.length.eq(npixels >> 1),
                                  1: self.video_framebuffer.fb_dma.length.eq(npixels >> 2),
                                  0: self.video_framebuffer.fb_dma.length.eq(npixels >> 3),
                              }),
                          ),
                       ),
                       If(~bt_upd & ~vres_upd & (post_reset_ctr == 1) & previous_videoctrl, # we've waited for the mode switch so restore video ctrl if set
                          videoctrl.eq(1),
                          videoctrl_upd.eq(1),
                          previous_videoctrl.eq(0), # reset, ow that the update is finished
                       ),
                       If(~bt_upd & ~vres_upd & (post_reset_ctr != 0),
                          post_reset_ctr.eq(post_reset_ctr - 1),
                       ),
        ]

        # videoctrl logic
        old_videoctrl = Signal()
        videoctrl_starting = Signal()
        videoctrl_stopping = Signal()
        self.sync += [
            # turn on
            If(videoctrl & videoctrl_upd & ~videoctrl_starting & ~videoctrl_stopping,
               If(~old_videoctrl,
                  self.video_framebuffer.fb_dma.enable.eq(1), # enable DMA
                  videoctrl_starting.eq(1),
                  videoctrl_upd.eq(0),
               ).Else( # already on, ignore?
                   videoctrl_upd.eq(0),
               )
            ),
            If(videoctrl_starting & (self.video_framebuffer.fb_dma.rsv_level != 0),
               vtg_enable.eq(1), # there's some data requested, good to go
               old_videoctrl.eq(1), # we're on
               videoctrl_starting.eq(0), # starting finished
            ),
            # turn off
            If(~videoctrl & videoctrl_upd & ~videoctrl_starting & ~videoctrl_stopping, # neg edge
               If(old_videoctrl,
                  self.video_framebuffer.fb_dma.enable.eq(0), # disable DMA
                  videoctrl_stopping.eq(1),
                  videoctrl_upd.eq(0),
               ).Else( # already off, ignore?
                   videoctrl_upd.eq(0),
               )
            ),
            If(videoctrl_stopping & (self.video_framebuffer.fb_dma.rsv_level == 0) & (self.video_framebuffer.underflow),
               vtg_enable.eq(0), # the DMA FIFO is purged, stop vtg
               old_videoctrl.eq(0),
               videoctrl_stopping.eq(0),
            ),
        ]
        
        self.comb += [ videoctrl_busy.eq(videoctrl_starting | videoctrl_stopping | in_reset | (post_reset_ctr != 0) | videoctrl_upd) ]
        
        # VBL logic
        self.sync += [
                      If(self.video_framebuffer.vblping == 1,
                         vbl_signal.eq(1),
                         ),]




        hdmi_width_bits = hbits # 12 enough for 2200 (frame width)
        hdmi_height_bits = vbits  # 12 (more than) enough for 1125 (frame height)
        
        hdmiext_frame_width = Signal(hdmi_width_bits)
        hdmiext_frame_height = Signal(hdmi_height_bits)
        hdmiext_screen_width = Signal(hdmi_width_bits)
        hdmiext_screen_height = Signal(hdmi_height_bits)
        
        ## INPUTS to the HDMI module
        hdmiext_audio_clk = Signal() # should be 44.1 kHz clock, fixme
        hdmiext_reset = Signal() # "synchronous reset back to 0,0"
        hdmiext_rgb = Signal(24) # three colors at 8 bits each, fixme
        hdmiext_audio_word_0 = Signal(16) # channel 0 of stereo audio, fixme
        hdmiext_audio_word_1 = Signal(16) # channel 1 of stereo audio, fixme

        self.submodules.goblin_audio = GoblinAudio(soc, 44.1e3)
        self.comb += [
            hdmiext_audio_clk.eq(self.goblin_audio.hdmiext_audio_clk),
            hdmiext_audio_word_0.eq(self.goblin_audio.hdmiext_audio_word_0),
            hdmiext_audio_word_1.eq(self.goblin_audio.hdmiext_audio_word_1),
        ]
        
        ## OUTPUTS from the HDMI module
        hdmiext_tmds = Signal(3) # high-speed colors to the TMDS bits
        hdmiext_tmds_clock = Signal() # high-speec clock to the TMDS bits
        #### for the TMDS above, I think I still need the OBUFDS used in Litex VideoS7HDMIPHY, as the hdmi module only does serialization & TMDS
        #### mmmm, yes there's some demo code available
        #### https://github.com/hdl-util/hdmi-demo/blob/d5e8d1f15617b4e021ae135b118ecb3e1795a138/top/sea/sea_top.sv#L50
        #### Verilog ddrout module added below

        hdmiext_cx = Signal(hdmi_width_bits) # current X
        hdmiext_cy = Signal(hdmi_height_bits) # current Y

        self.comb += [
            # always ready
            vfb.source.ready.eq(1),
            # ignore vfb.source.valid
            hdmiext_rgb[ 0: 8].eq(vfb.source.b),
            hdmiext_rgb[ 8:16].eq(vfb.source.g),
            hdmiext_rgb[16:24].eq(vfb.source.r),
        ##    hdmiext_audio_word_0.eq(0), # fixme: implement
        ##    hdmiext_audio_word_1.eq(0), # fixme: implement
            # use VTG enable to generate reset, to we have the same relationship to the DMA
            hdmiext_reset.eq(~vtg_enable),
        ]
        
        hdmi_sync = getattr(self.sync, "hdmi") # fixme, clock_domain parameter ?

        # in the FB we need to output the color by cycle 1, but are doing so after 3 cycles
        # so we need to anticipate cx by 2 cycles
        # we're delaying by 1 extra cycle from the original, so to anticipate by 2 cycles we need to add 3...
        hdmiext_cx_offset2 = Signal(hdmi_width_bits)
        hdmiframe_hres = hres + vtg.video_timings["h_blanking"]
        hdmi_sync += [
            If(hdmiext_cx == (hdmiframe_hres - 3),
                   hdmiext_cx_offset2.eq(0),
            ).Elif(hdmiext_cx == (hdmiframe_hres - 2),
                   hdmiext_cx_offset2.eq(1),
            ).Elif(hdmiext_cx == (hdmiframe_hres - 1),
                   hdmiext_cx_offset2.eq(2),
            ).Else(
                hdmiext_cx_offset2.eq(hdmiext_cx + 3)
            )
        ]

        # replacement for vtg's hactive, vactive 
        hactive = Signal(reset = 0)
        vactive = Signal(reset = 0)
        hdmi_sync += [
            If(hdmiext_cx_offset2 == vtg.hres_start,
               hactive.eq(1)),
            If(hdmiext_cx_offset2 == vtg.hres_end,
               hactive.eq(0)),
            If(hdmiext_cy == vtg.vres_start,
               vactive.eq(1)),
            If(hdmiext_cy == vtg.vres_end,
               vactive.eq(0)),
            If(hdmiext_reset,
               hactive.eq(0),
               vactive.eq(0)),
            vfb.last.eq((hdmiext_cx_offset2 == vtg.hres_end) & (hdmiext_cy == vtg.vres_end)),
        ]
        # replacement for vtg's hinframe, vinframe 
        hinframe = Signal(reset = 0)
        vinframe = Signal(reset = 0)
        hdmi_sync += [
            If(hdmiext_cx_offset2 == 0,
               hinframe.eq(1)),
            If(hdmiext_cx_offset2 == hres,
               hinframe.eq(0)),
            If(hdmiext_cy == 0,
               vinframe.eq(1)),
            If(hdmiext_cy == vres,
               vinframe.eq(0)),
            If(hdmiext_reset,
               hinframe.eq(0),
               vinframe.eq(0)),
        ]
        # generate de for the FB
        self.comb += [
            vfb.de.eq(hactive & vactive),
            vfb.inframe.eq(hinframe & vinframe),
        ]

        ### basic 44.1 KHz clock based on the HDMI clock
        ##audio_max = int((vtg.video_timings["pix_clk"] / 44100.0) + 0.5)
        ##audio_max_bits = log2_int(audio_max, False)
        ##audio_counter = Signal(audio_max_bits)
        ##hdmi_sync += [
        ##    If(audio_counter == (audio_max - 1),
        ##       hdmiext_audio_clk.eq(1),
        ##       audio_counter.eq(0),
        ##    ).Else(
        ##        hdmiext_audio_clk.eq(0),
        ##        audio_counter.eq(audio_counter + 1),
        ##    ),
        ##]
        
        self.specials += Instance("hdmi",
                                  p_VIDEO_ID_CODE = 16, # CEA-861-D, "4.15 1920x1080p @ 59.94/60Hz (Format 16)", FIXME
                                  p_IT_CONTENT = 1,
                                  p_BIT_WIDTH = hdmi_width_bits,
                                  p_BIT_HEIGHT = hdmi_height_bits,
                                  p_DVI_OUTPUT = 0, # 
                                  # **All parameters below matter ONLY IF you plan on sending auxiliary data (DVI_OUTPUT == 1'b0)**
                                  p_VIDEO_REFRESH_RATE = 60.0, # so for 148.5 MHz
                                  p_AUDIO_RATE = 44100,
                                  p_AUDIO_BIT_WIDTH = 16,
                                  p_VENDOR_NAME = "RD\0\0\0\0\0\0", # Must be 8 bytes null-padded 7-bit ASCII
                                  p_PRODUCT_DESCRIPTION = "NuBusFPGA HDMI\0\0", # Must be 16 bytes null-padded 7-bit ASCII
                                  p_SOURCE_DEVICE_INFORMATION = 9, # See CTA-861-G for the list of valid codes, 9 == 'PC General'
                                  p_START_X = 0,
                                  p_START_Y = 0,
                                  i_clk_pixel_x5 = ClockSignal("hdmi5x"), # fixme, clock_domain parameter ?
                                  i_clk_pixel = ClockSignal("hdmi"), # fixme, clock_domain parameter ?
                                  i_clk_audio = hdmiext_audio_clk,
                                  i_reset = hdmiext_reset,
                                  i_rgb = hdmiext_rgb,
                                  i_audio_sample_word = Cat(hdmiext_audio_word_0, hdmiext_audio_word_1),
                                  # These outputs go to the HDMI port
                                  o_tmds = hdmiext_tmds,
                                  o_tmds_clock = hdmiext_tmds_clock,
                                  # All outputs below this line stay inside the FPGA
                                  o_cx = hdmiext_cx, # position in _frame_
                                  o_cy = hdmiext_cy, # position in _frame_
                                  o_frame_width = hdmiext_frame_width,
                                  o_frame_height = hdmiext_frame_height,
                                  o_screen_width = hdmiext_screen_width,
                                  o_screen_height = hdmiext_screen_height)

        hdmi_pads = platform.request("hdmi")
        self.specials += Instance("hdmiext_ddrout",
                                  i_tmds = hdmiext_tmds,
		                  i_tmds_clock = hdmiext_tmds_clock,
		                  o_r_pad_p = hdmi_pads.data2_p,
		                  o_r_pad_n = hdmi_pads.data2_n,
		                  o_g_pad_p = hdmi_pads.data1_p,
		                  o_g_pad_n = hdmi_pads.data1_n,
		                  o_b_pad_p = hdmi_pads.data0_p,
		                  o_b_pad_n = hdmi_pads.data0_n,
		                  o_clk_pad_p = hdmi_pads.clk_p,
		                  o_clk_pad_n = hdmi_pads.clk_n);
        
    def add_sources(self, platform):
        platform.add_source("VintageBusFPGA_Common/hdmiext_ddrout.v", "verilog")
        platform.add_source("hdl-util_hdmi/src/hdmi.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/audio_clock_regeneration_packet.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/audio_info_frame.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/audio_sample_packet.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/auxiliary_video_information_info_frame.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/packet_assembler.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/packet_picker.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/serializer.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/source_product_description_info_frame.sv", "verilog")
        platform.add_source("hdl-util_hdmi/src/tmds_channel.sv", "verilog")
