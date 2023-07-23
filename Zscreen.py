from migen import *
from migen.genlib.fifo import *
from litex.soc.interconnect.csr import *

class Zscreen(Module, AutoCSR):
    def __init__(self, platform, wb, width=1920, height=1080, depth=8):

        self.trace_data = trace_data = CSRStorage(32, description = "trace_data")

        self.submodules.fifo = fifo = SyncFIFOBuffered(width=32,depth=128)

        self.comb += [
            fifo.din.eq(trace_data.storage),
            fifo.we.eq(trace_data.re),
        ]

        #curx = Signal(12, reset = (width-136))
        #cury = Signal(12, reset = (8))

        default_address =   (0x8f800000 + (width-138) + (width*24)   ) // 4 # FIXME: for 8 MiB FB only IMPROVEME: assumes 32-bits WB
        last_address =      (0x8f800000 + (width-138) + (width*1072)) // 4 # FIXME: for 8 MiB FB only IMPROVEME: assumes 32-bits WB
        address_increment = (width) // 4
        #default_address = (0x8f800000 + width//2 + width*height//2) // 4
        #last_address = (0x8f800000 + width//2 + width*(height-8)) // 4
        #address_increment = (width) // 4
        base_address = Signal(30, reset = default_address) # IMPROVEME: assumes 32-bits WB
        cur_address = Signal(30)

        print(f"TRACE: displaying @ 0x{default_address*4:08x} with increment {address_increment*4}")
        
        cur_nib_idx = Signal(3)
        cur_line_idx = Signal(3)

        val = Signal(32)
        
        cur_nib = Signal(4)
        self.comb += [
            Case((cur_nib_idx ^ 1), { ## nibble-swap for proper order
                x: cur_nib.eq(val[(4*x):(4*x+4)]) for x in range(0, 8)
            }),
        ]
        cur_nib_decoded = Signal(8)
        self.submodules.fsm = fsm = FSM(reset_state="Reset")

        saw_ongoing = Signal()
        saw_re = Signal()
        saw_readable= Signal()
        self.sync += [
            If(~fsm.ongoing("Idle"),
               saw_ongoing.eq(1),
            ),
            If(trace_data.re,
               saw_re.eq(1),
            ),
            If(fifo.readable,
               saw_readable.eq(1),
            ),
        ]

        if (False):
            led0 = platform.request("user_led", 0)
            led1 = platform.request("user_led", 1)
            led2 = platform.request("user_led", 2)
            led3 = platform.request("user_led", 3)
            led4 = platform.request("user_led", 4)
            led5 = platform.request("user_led", 5)
            led6 = platform.request("user_led", 6)
            led7 = platform.request("user_led", 7)
            
            self.comb += [
                led0.eq(~fsm.ongoing("Idle")),
                led1.eq(trace_data.re),
                led2.eq(fifo.readable),
                led3.eq(0),
                
                led4.eq(saw_ongoing),
                led5.eq(saw_re),
                led6.eq(saw_readable),
                led7.eq(trace_data.storage[0]),
            ]

        # set up wishbone
        self.comb += [
            wb.we.eq(1),
            wb.sel.eq(0xF),
            wb.adr.eq(cur_address),
        ]
        
        fsm.act("Reset",
                NextState("Idle"),
        )
        fsm.act("Idle",
                If(fifo.readable,
                   NextValue(val, fifo.dout),
                   NextValue(cur_line_idx, 0),
                   NextValue(cur_nib_idx, 0),
                   NextValue(cur_address, base_address),
                   fifo.re.eq(1),
                   NextState("StartWriteLow"),
                ),
        )
        fsm.act("StartWriteLow",
                wb.cyc.eq(1),
                wb.stb.eq(1),
                wb.dat_w.eq(Cat(Replicate(cur_nib_decoded[7], 8), Replicate(cur_nib_decoded[6], 8), Replicate(cur_nib_decoded[5], 8), Replicate(cur_nib_decoded[4], 8))),
                If(wb.ack,
                   NextValue(cur_address, cur_address + 1),
                   NextState("StartWriteHigh"),
                ),
        )
        fsm.act("StartWriteHigh",
                wb.cyc.eq(1),
                wb.stb.eq(1),
                wb.dat_w.eq(Cat(Replicate(cur_nib_decoded[3], 8), Replicate(cur_nib_decoded[2], 8), Replicate(cur_nib_decoded[1], 8), Replicate(cur_nib_decoded[0], 8))),
                If(wb.ack,
                   If((cur_line_idx == 7) & (cur_nib_idx == 7),
                      #If(base_address == last_address,
                      #   NextValue(base_address, default_address),
                      #).Else(
                         NextValue(base_address, base_address + address_increment),
                      #),
                      NextState("Idle"),
                   ).Elif(cur_nib_idx == 7,
                          NextValue(base_address, base_address + address_increment),
                          NextValue(cur_address, base_address + address_increment),
                          NextValue(cur_nib_idx, 0),
                          NextValue(cur_line_idx, cur_line_idx + 1),
                          NextState("StartWriteLow"),
                   ).Else(
                       NextValue(cur_address, cur_address + 1),
                       NextValue(cur_nib_idx, cur_nib_idx + 1),
                       NextState("StartWriteLow"),
                   )
                ),
        )

        self.comb += [
            Case((cur_line_idx), {
                0: cur_nib_decoded.eq(0),
                7: cur_nib_decoded.eq(0),
                1: Case(cur_nib, {
                    0:cur_nib_decoded.eq(0x18), 1:cur_nib_decoded.eq(0x10), 2:cur_nib_decoded.eq(0x18), 3:cur_nib_decoded.eq(0x38), 4:cur_nib_decoded.eq(0x20), 5:cur_nib_decoded.eq(0x3c), 6:cur_nib_decoded.eq(0x1c), 7:cur_nib_decoded.eq(0x3c), 8:cur_nib_decoded.eq(0x18), 9:cur_nib_decoded.eq(0x18), 10:cur_nib_decoded.eq(0x18), 11:cur_nib_decoded.eq(0x38), 12:cur_nib_decoded.eq(0x18), 13:cur_nib_decoded.eq(0x38), 14:cur_nib_decoded.eq(0x3c), 15:cur_nib_decoded.eq(0x3c),
                }),
                2: Case(cur_nib, {
                    0:cur_nib_decoded.eq(0x24), 1:cur_nib_decoded.eq(0x30), 2:cur_nib_decoded.eq(0x24), 3:cur_nib_decoded.eq(0x04), 4:cur_nib_decoded.eq(0x28), 5:cur_nib_decoded.eq(0x20), 6:cur_nib_decoded.eq(0x20), 7:cur_nib_decoded.eq(0x04), 8:cur_nib_decoded.eq(0x24), 9:cur_nib_decoded.eq(0x24), 10:cur_nib_decoded.eq(0x24), 11:cur_nib_decoded.eq(0x24), 12:cur_nib_decoded.eq(0x24), 13:cur_nib_decoded.eq(0x24), 14:cur_nib_decoded.eq(0x20), 15:cur_nib_decoded.eq(0x20),
                }),
                3: Case(cur_nib, {
                    0:cur_nib_decoded.eq(0x2c), 1:cur_nib_decoded.eq(0x10), 2:cur_nib_decoded.eq(0x04), 3:cur_nib_decoded.eq(0x18), 4:cur_nib_decoded.eq(0x28), 5:cur_nib_decoded.eq(0x38), 6:cur_nib_decoded.eq(0x38), 7:cur_nib_decoded.eq(0x08), 8:cur_nib_decoded.eq(0x18), 9:cur_nib_decoded.eq(0x24), 10:cur_nib_decoded.eq(0x24), 11:cur_nib_decoded.eq(0x38), 12:cur_nib_decoded.eq(0x20), 13:cur_nib_decoded.eq(0x24), 14:cur_nib_decoded.eq(0x38), 15:cur_nib_decoded.eq(0x38),
                }),
                4: Case(cur_nib, {
                    0:cur_nib_decoded.eq(0x34), 1:cur_nib_decoded.eq(0x10), 2:cur_nib_decoded.eq(0x18), 3:cur_nib_decoded.eq(0x04), 4:cur_nib_decoded.eq(0x3c), 5:cur_nib_decoded.eq(0x04), 6:cur_nib_decoded.eq(0x24), 7:cur_nib_decoded.eq(0x10), 8:cur_nib_decoded.eq(0x24), 9:cur_nib_decoded.eq(0x1c), 10:cur_nib_decoded.eq(0x3c), 11:cur_nib_decoded.eq(0x24), 12:cur_nib_decoded.eq(0x20), 13:cur_nib_decoded.eq(0x24), 14:cur_nib_decoded.eq(0x20), 15:cur_nib_decoded.eq(0x20),
                }),
                5: Case(cur_nib, {
                    0:cur_nib_decoded.eq(0x24), 1:cur_nib_decoded.eq(0x10), 2:cur_nib_decoded.eq(0x20), 3:cur_nib_decoded.eq(0x04), 4:cur_nib_decoded.eq(0x08), 5:cur_nib_decoded.eq(0x04), 6:cur_nib_decoded.eq(0x24), 7:cur_nib_decoded.eq(0x10), 8:cur_nib_decoded.eq(0x24), 9:cur_nib_decoded.eq(0x04), 10:cur_nib_decoded.eq(0x24), 11:cur_nib_decoded.eq(0x24), 12:cur_nib_decoded.eq(0x24), 13:cur_nib_decoded.eq(0x24), 14:cur_nib_decoded.eq(0x20), 15:cur_nib_decoded.eq(0x20),
                }),
                6: Case(cur_nib, {
                    0:cur_nib_decoded.eq(0x18), 1:cur_nib_decoded.eq(0x38), 2:cur_nib_decoded.eq(0x3c), 3:cur_nib_decoded.eq(0x38), 4:cur_nib_decoded.eq(0x08), 5:cur_nib_decoded.eq(0x38), 6:cur_nib_decoded.eq(0x18), 7:cur_nib_decoded.eq(0x10), 8:cur_nib_decoded.eq(0x18), 9:cur_nib_decoded.eq(0x38), 10:cur_nib_decoded.eq(0x24), 11:cur_nib_decoded.eq(0x38), 12:cur_nib_decoded.eq(0x18), 13:cur_nib_decoded.eq(0x38), 14:cur_nib_decoded.eq(0x3c), 15:cur_nib_decoded.eq(0x20),
                }),
            }
            ),
        ]
        
