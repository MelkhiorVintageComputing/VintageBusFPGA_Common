from migen import *
from migen.genlib.fifo import *
from migen.genlib.cdc import BusSynchronizer
from litex.soc.interconnect.csr import *
from litex.soc.interconnect import wishbone
from litex.soc.interconnect import stream

# width of towrite_fifo is '32'+'burst_size * 32' (vaddr + data)
# so the SBus DMA has all the needed info
# width of fromsbus_req_fifo is 'blk_addr_width' + 'vaddr' (blk_addr + vaddr)
# width of fromsbus_fifo is 'blk_addr_width' + 'burst_size * 32' (blk_addr + data)
# the blk_addr does the round-trip to accompany the data
class ExchangeWithSD(Module, AutoCSR):
    def __init__(self, soc, platform, tosbus_fifo, fromsbus_fifo, fromsbus_req_fifo, sd_source, sd_sink, burst_size = 4, clock_domain="sbus"):
        self.tosbus_fifo = tosbus_fifo
        self.fromsbus_fifo = fromsbus_fifo
        self.fromsbus_req_fifo = fromsbus_req_fifo

        fifo_depth_read = 1024
        fifo_depth_write = 128
        
        tosbus_fifo_din = Record(soc.tosbus_layout)
        self.comb += self.tosbus_fifo.din.eq(tosbus_fifo_din.raw_bits())
        fromsbus_req_fifo_din = Record(soc.fromsbus_req_layout)
        self.comb += self.fromsbus_req_fifo.din.eq(fromsbus_req_fifo_din.raw_bits())
        fromsbus_fifo_dout = Record(soc.fromsbus_layout)
        self.comb += fromsbus_fifo_dout.raw_bits().eq(self.fromsbus_fifo.dout)

        data_width = burst_size * 4
        data_width_bits = burst_size * 32
        blk_addr_width = 32 - log2_int(data_width) # 27 for burst_size == 8; 28 for burst_size == 4

        # sd source and sink are 8 bits, buffer and convert
        self.submodules.sink_fifo      = stream.SyncFIFO([("data", 8)], fifo_depth_read, buffered=True)
        self.submodules.sink_converter = stream.Converter(8, data_width_bits, reverse=True)
        self.submodules.source_converter = stream.Converter(data_width_bits, 8, reverse=True)
        self.submodules.source_fifo      = stream.SyncFIFO([("data", 8)], fifo_depth_write, buffered=True)
        # data coming into this (so originated by sd_source)
        sd_source.connect(self.sink_fifo.sink) # cleanme
        self.sink_fifo.source.connect(self.sink_converter.sink)
        # data going out of this (so consumed by sd_sink)
        self.source_converter.source.connect(self.source_fifo.sink)
        self.source_fifo.source.connect(sd_sink) # cleanme
        
        local_r_addr = Signal(blk_addr_width)
        dma_r_addr = Signal(32)
        max_block_bits=16

        # same set of CSRs as ExchangeWithMem
        self.blk_size = CSRStatus(32) # report the block size to the SW layer
        self.blk_base = CSRStatus(32) # report where the blk starts # makes no sense for sd-card ? # FIXME
        self.mem_size = CSRStatus(32) # report how much memory we have # makes no sense for sd-card ? # FIXME
        self.comb += self.blk_size.status.eq(data_width)
        self.comb += self.blk_base.status.eq(0 >> log2_int(data_width)) # FIXME
        self.comb += self.mem_size.status.eq((0 * 1024 * 1024) >> log2_int(data_width)) # FIXME

        self.irqctrl = CSRStorage(write_from_dev=True, fields = [CSRField("irq_enable", 1, description = "Enable interrupt"),
                                                                 CSRField("irq_clear", 1, description = "Clear interrupt"),
                                                                 CSRField("reserved", 30, description = "Reserved"),
        ])
        self.blk_addr =   CSRStorage(32, description = "SDCard Block address to read/write from Wishbone memory (block of size {})".format(data_width)) # FIXME Status only
        self.dma_addr =   CSRStorage(32, description = "Host Base address where to write/read data (i.e. SPARC Virtual addr)")
        self.blk_cnt = CSRStorage(write_from_dev=True, fields = [CSRField("blk_cnt", max_block_bits, description = "How many blk to read/write (max 2^{}-1)".format(max_block_bits)),
                                                                 CSRField("rsvd", 32 - (max_block_bits + 1), description = "Reserved"),
                                                                 CSRField("rd_wr", 1, description = "Read/Write selector"),
        ])
        self.last_blk =   CSRStatus(32, description = "Last Blk addr finished on WB side")
        self.last_dma =   CSRStatus(32, description = "Last DMA addr finished on WB side")
        self.dma_wrdone = CSRStatus(32, description = "DMA Block written to SDCard", reset = 0)
        self.blk_rem =    CSRStatus(32, description = "How many block remaining; bit 31 is RD", reset = 0)
        self.dma_status = CSRStatus(fields = [CSRField("rd_fsm_busy", 1, description = "Read FSM is doing some work"),
                                              CSRField("wr_fsm_busy", 1, description = "Write FSM is doing some work"),
                                              CSRField("has_wr_data", 1, description = "Data available to write to SDCard"),
                                              CSRField("has_requests", 1, description = "There's outstanding requests to the SBus"),
                                              CSRField("has_rd_data", 1, description = "Data available to write to SBus"),
                                              CSRField("reserved", 27, description = "Reserved")
        ])
        self.wr_tosdram = CSRStatus(32, description = "Last address written to SDCard")
        self.irqstatus = CSRStatus(fields = [ CSRField("irq", 1, description = "There's a pending interrupt"),
                                              CSRField("reserved", 31, description = "Reserved")
        ])

        #if (do_checksum):
        self.checksum = CSRStorage(data_width_bits, write_from_dev=True, description = "checksum (XOR)"); # unused, FIXME
        
        self.submodules.req_r_fsm = req_r_fsm = FSM(reset_state="Reset") # checkme
        self.submodules.req_w_fsm = req_w_fsm = FSM(reset_state="Reset") # checkme

        self.comb += self.dma_status.fields.rd_fsm_busy.eq(~req_r_fsm.ongoing("Idle")) # Read FSM Busy
        self.comb += self.dma_status.fields.wr_fsm_busy.eq(~req_w_fsm.ongoing("Idle")) # Write FSM Busy
        self.comb += self.dma_status.fields.has_wr_data.eq(self.fromsbus_fifo.readable) # Some data available to write to memory

        # The next two status bits reflect stats in the SBus clock domain
        self.submodules.fromsbus_req_fifo_readable_sync = BusSynchronizer(width = 1, idomain = clock_domain, odomain = "sys")
        fromsbus_req_fifo_readable_in_sys = Signal()
        self.comb += self.fromsbus_req_fifo_readable_sync.i.eq(self.fromsbus_req_fifo.readable)
        self.comb += fromsbus_req_fifo_readable_in_sys.eq(self.fromsbus_req_fifo_readable_sync.o)

        # w/o this extra delay, the driver sees an outdated checksum for some reason... # fixme: from ExchangeWithMem
        # there's probably a more fundamental issue :-(
        # note: replaced PulseSynchronizer with BusSynchronizer, should I retry w/o this ?
        fromsbus_req_fifo_readable_in_sys_cnt = Signal(5)
        self.sync += If(fromsbus_req_fifo_readable_in_sys,
                        fromsbus_req_fifo_readable_in_sys_cnt.eq(0x1F)
                     ).Else(
                         If(fromsbus_req_fifo_readable_in_sys_cnt > 0,
                            fromsbus_req_fifo_readable_in_sys_cnt.eq(fromsbus_req_fifo_readable_in_sys_cnt - 1)
                         )
                     )
        self.comb += self.dma_status.fields.has_requests.eq(fromsbus_req_fifo_readable_in_sys | (fromsbus_req_fifo_readable_in_sys_cnt != 0)) # we still have outstanding requests, or had recently

        self.submodules.tosbus_fifo_readable_sync = BusSynchronizer(width = 1, idomain = clock_domain, odomain = "sys")
        tosbus_fifo_readable_in_sys = Signal()
        self.comb += self.tosbus_fifo_readable_sync.i.eq(self.tosbus_fifo.readable)
        self.comb += tosbus_fifo_readable_in_sys.eq(self.tosbus_fifo_readable_sync.o)
        self.comb += self.dma_status.fields.has_rd_data.eq(tosbus_fifo_readable_in_sys)  # there's still data to be sent to memory; this will drop before the last SBus Master Cycle is finished, but then the SBus is busy so the host won't be able to read the status before the cycle is finished so we're good

        ongoing_m1 = Signal()
        ongoing = Signal()
        temp_irq = Signal() # active high
        self.irq = Signal() # active low

        self.sync += ongoing_m1.eq(ongoing)
        self.sync += ongoing.eq(self.dma_status.fields.rd_fsm_busy  |
                                self.dma_status.fields.wr_fsm_busy  |
                                self.dma_status.fields.has_wr_data  |
                                self.dma_status.fields.has_requests |
                                self.dma_status.fields.has_rd_data  |
                                (self.blk_cnt.fields.blk_cnt != 0))
        
        self.sync += temp_irq.eq((ongoing_m1 & ~ongoing) | # irq on falling edge of ongoing
                                 (temp_irq & ~self.irqctrl.fields.irq_clear & ~(~ongoing_m1 & ongoing))) # keep irq until cleared or rising edge of ongoing
        
        self.comb += self.irq.eq(~(temp_irq & self.irqctrl.fields.irq_enable))
        self.comb += self.irqstatus.fields.irq.eq(~self.irq)
        
        self.sync += If(self.irqctrl.fields.irq_clear, ## auto-reset irq_clear
                        self.irqctrl.we.eq(1),
                        self.irqctrl.dat_w.eq(self.irqctrl.storage & 0xFFFFFFFD)).Else(
                            self.irqctrl.we.eq(0),
                        )

        led0 = platform.request("user_led", 0)
        led1 = platform.request("user_led", 1)

        self.comb += [ led0.eq(self.sink_converter.source.valid), ]
        #self.comb += [ led0.eq(~self.tosbus_fifo.writable), ]
        self.comb += [ led1.eq(sd_source.valid), ]

        req_r_fsm.act("Reset",
                    NextState("Idle")
        )
        req_r_fsm.act("Idle",
                    If(((self.blk_cnt.fields.blk_cnt != 0) & # checking self.blk_cnt.re might be too transient ? -> need to auto-reset
                        (~self.blk_cnt.fields.rd_wr)), # !read -> write
                       NextValue(local_r_addr, self.blk_addr.storage),
                       NextValue(dma_r_addr, self.dma_addr.storage),
                       NextValue(self.blk_rem.status, Cat(self.blk_cnt.fields.blk_cnt, Signal(32-max_block_bits, reset = 0))),
                       NextState("ReqFromMemory")
                    ).Elif(((self.blk_cnt.fields.blk_cnt != 0) & # checking self.blk_cnt.re might be too transient ? -> need to auto-reset
                            (self.blk_cnt.fields.rd_wr)), # read
                           NextValue(local_r_addr, self.blk_addr.storage),
                           NextValue(dma_r_addr, self.dma_addr.storage),
                           NextValue(self.blk_rem.status, Cat(self.blk_cnt.fields.blk_cnt, Signal(32-max_block_bits, reset = 0))),
                           NextState("QueueReqToMemory")
                    )
        )
        self.comb += [ tosbus_fifo_din.data.eq(self.sink_converter.source.data), ]
        req_r_fsm.act("ReqFromMemory", # in ExchangeWithMem we need to request with the proper address, but in SDcard the SW is responsible for asking the SDCard to send data in the FIFO, so this is more like "WaitForData"
                      If(self.sink_converter.source.valid & self.tosbus_fifo.writable,
                         self.tosbus_fifo.we.eq(1),
                         self.sink_converter.source.ready.eq(1),
                         tosbus_fifo_din.address.eq(dma_r_addr),
                         NextValue(self.last_blk.status, local_r_addr),
                         NextValue(self.last_dma.status, dma_r_addr),
                         NextValue(self.blk_rem.status, self.blk_rem.status - 1),
                         If(self.blk_rem.status[0:max_block_bits] <= 1,
                            self.blk_cnt.we.eq(1), ## auto-reset
                            self.blk_cnt.dat_w.eq(0),
                            NextState("Idle"),
                         ).Else(
                             NextValue(local_r_addr, local_r_addr + 1),
                             NextValue(dma_r_addr, dma_r_addr + data_width),
                             NextState("ReqFromMemory"), # redundant
                         )
                      )
        )
        req_r_fsm.act("QueueReqToMemory", # identical to ExchangeWithMem
                      If(self.fromsbus_req_fifo.writable,
                         self.fromsbus_req_fifo.we.eq(1),
                         fromsbus_req_fifo_din.blkaddress.eq(local_r_addr),
                         fromsbus_req_fifo_din.dmaaddress.eq(dma_r_addr),
                         NextValue(self.last_blk.status, local_r_addr),
                         NextValue(self.last_dma.status, dma_r_addr),
                         NextValue(self.blk_rem.status, self.blk_rem.status - 1),
                         If(self.blk_rem.status[0:max_block_bits] <= 1,
                            self.blk_cnt.we.eq(1), ## auto-reset
                            self.blk_cnt.dat_w.eq(0),
                            NextState("Idle"),
                         ).Else(
                             NextValue(local_r_addr, local_r_addr + 1),
                             NextValue(dma_r_addr, dma_r_addr + data_width),
                             NextValue(self.blk_rem.status, self.blk_rem.status - 1),
                             NextState("QueueReqToMemory"), #redundant
                         )
                      )
        )
        
        # data comming back from SBus
        req_w_fsm.act("Reset",
                    NextState("Idle")
        )
        self.comb += [ self.source_converter.sink.data.eq(fromsbus_fifo_dout.data), ]
        req_w_fsm.act("Idle", # does that really need an FSM ?
                      If(self.fromsbus_fifo.readable & self.source_converter.sink.ready,
                         self.fromsbus_fifo.re.eq(1),
                         self.source_converter.sink.valid.eq(1),
                         NextValue(self.wr_tosdram.status, fromsbus_fifo_dout.blkaddress),
                         NextState("Idle"),
                      )
        )
