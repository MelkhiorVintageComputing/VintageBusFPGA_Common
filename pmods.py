#
# Copyright (c) 2026 Romain Dolbeau <romain@dolbeau.org>
# SPDX-License-Identifier: BSD-2-Clause

# PMod modules, for any board that declares its 12-pin PMod host connector(s)
# as a LiteX connector of 8 pins in Digilent order:
#
#     connector index:  0  1  2  3  4  5  6  7
#     Digilent pin   :  1  2  3  4  7  8  9 10
#
# (Digilent PMod spec: pins 1-6 on the upper row, 7-12 on the lower row, pin 1
# opposite the power pins; 5/11 are GND and 6/12 are VCC.)
#
# e.g. ("P1", "<pin1> <pin2> <pin3> <pin4> <pin7> <pin8> <pin9> <pin10>")
#
# Some hosts are "backward": the module only fits upside-down (IIsiFPGA V1.0,
# so that its LEDs face up when the card itself faces down in a 90° adapter).
# The module's upper row then meets the host's lower row: module pins 1-4 land
# on host pins 7-10 and 7-10 on 1-4. Pass upside_down=True for such hosts; the
# connector itself stays in the host's own Digilent order.

from litex.build.generic_platform import Pins, Subsignal, IOStandard, Misc

_digilent_to_index = { 1: 0, 2: 1, 3: 2, 4: 3, 7: 4, 8: 5, 9: 6, 10: 7 }

_upside_down = { 1: 7, 2: 8, 3: 9, 4: 10, 7: 1, 8: 2, 9: 3, 10: 4 }

def pmod_pin(pmod, pin, upside_down=False):
    """LiteX connector reference for module pin 'pin' (Digilent 1-4, 7-10) on PMod connector 'pmod'."""
    if upside_down:
        pin = _upside_down[pin]
    return f"{pmod}:{_digilent_to_index[pin]}"

def pmod_pins(pmod, pins, upside_down=False):
    """Pins() for a list of module pin numbers (Digilent) on connector 'pmod'."""
    return Pins(" ".join(pmod_pin(pmod, p, upside_down) for p in pins))

# PMOD-LEDS.SIMPLE: 8 LEDs (D1..D8, nets LED0..LED7, in a line on the board),
# active high, with series resistors to GND. From its KiCad files (J1 is a
# right-angle 2x6 header; its odd pads are the upper row, pad 1/2 VCC):
#     Digilent pin:  1     2     3     4     7     8     9     10
#     LED        :  LED1  LED3  LED5  LED7  LED0  LED2  LED4  LED6
# so diag_leds[i] drives LEDi (Di+1), in physical order.
_pmod_leds_simple_pins = [ 7, 1, 8, 2, 9, 3, 10, 4 ] # LED0 .. LED7

def diag_leds_pmod_io(pmod, name="diag_leds", upside_down=False):
    return [
        (name, 0, pmod_pins(pmod, _pmod_leds_simple_pins, upside_down), IOStandard("LVCMOS33")),
    ]

# Digilent PmodMicroSD (rev. A.1, schematic 500-380): microSD slot, no level
# shifting, 20k pull-ups to VCC on every line (on the module).
#     Digilent pin:  1            2            3             4         7     8     9   10
#     signal      :  CS/CD/DAT3   MOSI/CMD/DI  MISO/DAT0/DO  SCLK/CLK  DAT1  DAT2  CD  NC/EN
# CD is the slot's card-detect switch, pulled up (R13) and switched to GND by
# the slot: active low (low = card present). Pin 10 only reaches the (not
# loaded) inrush limiter: unused. The FPGA pull-ups below are redundant with
# the module's but kept, as in LiteX.
# Same as litex-boards' sdcard_pmod_io(), but in Digilent pin numbers.
# "sdcard" is for the native 4-bit LiteSDCard PHY (add_sdcard /
# add_sdcard_custom), "spisdcard" for SPI mode (add_spi_sdcard); request one.
def sdcard_pmod_io(pmod, upside_down=False):
    def p(*pins):
        return pmod_pins(pmod, pins, upside_down)
    return [
        ("spisdcard", 0,
            Subsignal("clk",  p(4)),
            Subsignal("mosi", p(2), Misc("PULLUP True")),
            Subsignal("cs_n", p(1), Misc("PULLUP True")),
            Subsignal("miso", p(3), Misc("PULLUP True")),
            Misc("SLEW=FAST"),
            IOStandard("LVCMOS33"),
        ),
        ("sdcard", 0,
            Subsignal("data", p(3, 7, 8, 1), Misc("PULLUP True")), # DAT0 .. DAT3
            Subsignal("cmd",  p(2), Misc("PULLUP True")),
            Subsignal("clk",  p(4)),
            Subsignal("cd",   p(9)),
            Misc("SLEW=FAST"),
            IOStandard("LVCMOS33"),
        ),
    ]
