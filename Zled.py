from migen import *
from migen.genlib.fifo import *
from litex.soc.interconnect.csr import *

class Zled(Module, AutoCSR):
    def __init__(self, platform):

        self.data0 = data0 = CSRStorage(32, description = "data 0")
        self.data1 = data1 = CSRStorage(32, description = "data 1")

        ctr_hundredth = Signal(20)
        ctr_count = Signal(7)

        leds = platform.request_all("user_led")

        self.submodules.fsm = fsm = FSM(reset_state="Reset")

        self.sync += [
            If(ctr_hundredth != 0,
               ctr_hundredth.eq(ctr_hundredth - 1),
            ).Else(
                ctr_hundredth.eq(1000000),
                If(ctr_count != 0,
                   ctr_count.eq(ctr_count - 1),
                ),
            )
        ]

        display_idx = Signal(5, reset = 0x1F)
        self.comb += [
            Case(display_idx, {
                0x00:    [ leds.eq(data0.storage[ 0: 8]), ],
                0x01:    [ leds.eq(data0.storage[ 8:16]), ],
                0x02:    [ leds.eq(data0.storage[16:24]), ],
                0x03:    [ leds.eq(data0.storage[24:32]), ],
                0x04:    [ leds.eq(data1.storage[ 0: 8]), ],
                0x05:    [ leds.eq(data1.storage[ 8:16]), ],
                0x06:    [ leds.eq(data1.storage[16:24]), ],
                0x07:    [ leds.eq(data1.storage[24:32]), ],
                0x08:    [ leds.eq(0x00), ],
                0x10:    [ leds.eq(0x01), ],
                0x11:    [ leds.eq(0x02), ],
                0x12:    [ leds.eq(0x04), ],
                0x13:    [ leds.eq(0x08), ],
                0x14:    [ leds.eq(0x10), ],
                0x15:    [ leds.eq(0x20), ],
                0x16:    [ leds.eq(0x40), ],
                0x17:    [ leds.eq(0x80), ],
                0x18:    [ leds.eq(0xFF), ],
                "default": [ leds.eq(0x00), ],
            }),
        ]

        bytenum = Signal(3)
        flashes = Signal(4)
        
        fsm.act("Reset",
                NextValue(ctr_count, 12),
                NextValue(display_idx, 0x10),
                NextState("March"),
        )
        ###################
        # must arrive with ctr_count == 12, display_idx == 0x10
        fsm.act("March",
                If((ctr_hundredth == 0) & (ctr_count == 0),
                   If(display_idx == 0x17, # finished
                      NextValue(ctr_count, 100),
                      NextValue(display_idx, 0x00),
                      NextValue(bytenum, 0),
                      NextState("Byte"),
                   ).Else(
                       NextValue(display_idx, display_idx + 1),
                       NextValue(ctr_count, 12),
                   )
                ),
        )
        ###################
        fsm.act("Byte",
                      If((ctr_hundredth == 0) & (ctr_count == 0),
                         If(bytenum == 0x7,
                            NextValue(ctr_count, 12),
                            NextValue(display_idx, 0x10),
                            NextState("March"),
                         ).Else(
                             NextValue(bytenum, bytenum + 1),
                             NextValue(ctr_count, 5),
                             NextValue(display_idx, 0x08),
                             NextValue(flashes, 5),
                             NextState("Flash"),
                         )
                      ),
        )
        ###################
        fsm.act("Flash",
                If((ctr_hundredth == 0) & (ctr_count == 0),
                   If(flashes == 0, # finished
                      NextValue(ctr_count, 100),
                      NextValue(display_idx, Cat(bytenum, Signal(len(display_idx) - len(bytenum), reset = 0))),
                      NextState("Byte"),
                   ).Else(
                       NextValue(display_idx, display_idx ^ 0x10),
                       NextValue(flashes, flashes - 1),
                       NextValue(ctr_count, 5),
                   )
                ),
        )
