from migen import *
from migen.genlib.fifo import *

import litex
from litex.soc.interconnect import wishbone

class WishboneDomainCrossingMaster(Module, wishbone.Interface):
    """Wishbone Clock Domain Crossing [Master]"""
    def __init__(self, platform, slave, cd_master="sys", cd_slave="sys", force_delay = 0):
        # Same Clock Domain, direct connection.
        wishbone.Interface.__init__(self, data_width=slave.data_width, adr_width=slave.adr_width)
        if cd_master == cd_slave:
            raise NameError("Don't use domain crossing for the same domains.")
        # Clock Domain Crossing.
        else:
            # request FIFO, to speed up bus turnaround on CPU side writes are fire-and-forget
            request_fifo_layout = [
                ("adr", slave.adr_width),
                ("data", slave.data_width),
                ("sel", slave.data_width//8),
                ("we", 1),
            ]
            self.submodules.request_fifo = request_fifo = ClockDomainsRenamer({"read": cd_slave, "write": cd_master})(AsyncFIFOBuffered(width=layout_len(request_fifo_layout), depth=16))
            request_fifo_dout = Record(request_fifo_layout)
            self.comb += request_fifo_dout.raw_bits().eq(request_fifo.dout)
            request_fifo_din = Record(request_fifo_layout)
            self.comb += request_fifo.din.eq(request_fifo_din.raw_bits())

            # response FIFO: data only
            self.submodules.response_fifo = response_fifo = ClockDomainsRenamer({"read": cd_master, "write": cd_slave})(AsyncFIFOBuffered(width=slave.data_width, depth=4))

            master_sync = getattr(self.sync, cd_master)
            slave_sync = getattr(self.sync, cd_slave)

            # request FIFO input is just Wishbone
            self.comb += [
                request_fifo_din.adr.eq(self.adr),
                request_fifo_din.data.eq(self.dat_w),
                request_fifo_din.sel.eq(self.sel),
                request_fifo_din.we.eq(self.we),
            ]
            wbm_cycle_ongoing = Signal(reset = 0)
            cyc_pending = Signal(reset = 0)
            wbm_ack_write = Signal(reset = 0)
            wbm_ack_read = Signal(reset = 0)
            master_sync += [
                request_fifo.we.eq(0),
                wbm_ack_write.eq(0),
                If(self.cyc & self.stb & ~wbm_cycle_ongoing, # if a new cycle starts
                   If(request_fifo.writable, # and we have space in the FIFO
                      request_fifo.we.eq(1), # strobe request FIFO
                      wbm_cycle_ongoing.eq(1),
                      If(self.we,
                         wbm_ack_write.eq(1), # write: fire and forget, immediate ACK of write
                      ),
                   ).Else( # new cycle, no space => remember we need to do it
                       cyc_pending.eq(1),
                   ),
                ),
                If(cyc_pending & request_fifo.writable, # some space at last, we push the request in the FIFO
                   cyc_pending.eq(0),
                   request_fifo.we.eq(1), # strobe request FIFO
                   wbm_cycle_ongoing.eq(1),
                   If(self.we,
                      wbm_ack_write.eq(1), # write: fire and forget, immediate ACK of write
                   ),
                ),
                If(wbm_ack_read | wbm_ack_write,
                   wbm_cycle_ongoing.eq(0),
                ),
            ]
            
            self.comb += [
                self.dat_r.eq(response_fifo.dout),
                wbm_ack_read.eq(response_fifo.readable), # ACK read as soon as data is available, hopefully there was a read request outstanding
                response_fifo.re.eq(1), # always instantaneous, we don't need to check writable as we have never more than 1 outstanding read request (not pipelined)
            ]

            self.comb += [
                self.ack.eq(wbm_ack_write | wbm_ack_read),
            ]

            self.comb += [
                slave.adr.eq(request_fifo_dout.adr),
                slave.dat_w.eq(request_fifo_dout.data),
                slave.sel.eq(request_fifo_dout.sel),
                slave.we.eq(request_fifo_dout.we),
                slave.cyc.eq(request_fifo.readable),
                slave.stb.eq(request_fifo.readable),
                
                request_fifo.re.eq(slave.ack),
                
                response_fifo.din.eq(slave.dat_r),
                response_fifo.we.eq(slave.ack & ~request_fifo_dout.we), # put the response if not a write
            ]
            
