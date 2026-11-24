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

from litex.build.generic_platform import Pins, IOStandard

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
