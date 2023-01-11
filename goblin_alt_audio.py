from migen import *
from migen.genlib.fifo import *
from litex.soc.interconnect.csr import *
from litex.soc.interconnect import wishbone

class GoblinAudio(Module, AutoCSR):
    def __init__(self, soc, audio_clk_freq):

        self.hdmiext_audio_clk    = hdmiext_audio_clk    = Signal() # should be audio_clk_freq/44.1 kHz clock
        self.hdmiext_audio_word_0 = hdmiext_audio_word_0 = Signal(16) # channel 0 of stereo audio (L-PCM)
        self.hdmiext_audio_word_1 = hdmiext_audio_word_1 = Signal(16) # channel 1 of stereo audio (L-PCM)

        self.irq = Signal() # active LOW

        self.busmaster = busmaster = wishbone.Interface()

        # # #

    
        self.irqctrl = CSRStorage(write_from_dev=True, fields = [CSRField("irq_enable", 1, description = "Enable interrupt"),
                                                                 CSRField("irq_clear", 1, description = "Clear interrupt"),
                                                                 CSRField("reserved", 30, description = "Reserved"),
        ])
        self.irqstatus = CSRStatus(fields = [ CSRField("irq", 1, description = "There's a pending interrupt"),
                                              CSRField("reserved", 31, description = "Reserved")
        ])

        
        self.ctrl = CSRStorage(write_from_dev=True, fields = [CSRField("buffer_num",  1, description = "Buffer to use"),
                                                              CSRField("reserved0",   7, description = "Reserved"),
                                                              CSRField("play",        1, description = "Play (start with specified buffer and keel looping over all buffers)"),
                                                              CSRField("reserved1",   7, description = "Reserved"),
                                                              CSRField("autostop",    1, description = "Autostop when currently playing buffer is empty"),
                                                              CSRField("reserved2",   7, description = "Reserved"),
                                                              CSRField("reserved3",   8, description = "Reserved"),
        ])
        self.bufstatus = CSRStatus(fields = [CSRField("buffer_num",   1, description = "Buffer in use"),
                                             CSRField("reserved0",    7, description = "Reserved"),
                                             CSRField("play",         1, description = "Playing"),
                                             CSRField("reserved1",    7, description = "Reserved"),
                                             CSRField("buffer_left", 16, description = "samples left"),
        ])
        self.buf0_addr = CSRStorage(32, description = "Wishbone base address for audio buffer 0")
        self.buf0_size = CSRStorage(fields = [CSRField("size",     16, description = "Number of samples in audio buffer 0"),
                                              CSRField("reserved", 16, description = "Reserved"),
        ])
        self.buf1_addr = CSRStorage(32, description = "Wishbone base address for audio buffer 1")
        self.buf1_size = CSRStorage(fields = [CSRField("size",     16, description = "Number of samples in audio buffer 1"),
                                              CSRField("reserved", 16, description = "Reserved"),
        ])
        
        self.buf_desc  = CSRStorage(fields = [CSRField("width",      1, description = "Sample width (0 = 16, 1 = 8)"),
                                              CSRField("reserved0",  5, description = "Reserved"),
                                              CSRField("mono",       1, description = "Mono (0 = Stereo, 1 = Mono)"),
                                              CSRField("signedness", 1, description = "Signedness (0 = signed, 1 = unsigned)"),
                                              CSRField("freq",       1, description = "Sample frequency (0 = 44.100 KHz, 1 = 22.050 KHz)"),
                                              CSRField("reserved1",  7, description = "Reserved"),
                                              CSRField("reserved2", 16, description = "Reserved"),
        ])
    
        # handle IRQ
        self.sync += If(self.irqctrl.fields.irq_clear, ## auto-reset irq_clear
                        self.irqctrl.we.eq(1),
                        self.irqctrl.dat_w.eq(self.irqctrl.storage & 0xFFFFFFFD)).Else(
                            self.irqctrl.we.eq(0),
                        )
        temp_irq = Signal() # long internal irq (can be masked)
        set_irq = Signal() # short transient irq (1 cycle ping from FSM)
        self.sync += temp_irq.eq(set_irq | # transient irq signal 
                                 (temp_irq & ~self.irqctrl.fields.irq_clear)) # keep irq until cleared
        self.comb += self.irq.eq(~(temp_irq & self.irqctrl.fields.irq_enable)) # only notify irq to the host if not disabled  # self.irq active low
        self.comb += self.irqstatus.fields.irq.eq(~self.irq) # self.irq active low

        # basic 44.1 KHz clock based on system clock
        audio_max = int((soc.sys_clk_freq / audio_clk_freq) + 0.5)
        audio_max_bits = log2_int(audio_max, False)
        audio_counter = Signal(audio_max_bits)
        self.sync += [
            If((audio_counter == (audio_max - 1)),
               hdmiext_audio_clk.eq(1),
               audio_counter.eq(0),
            ).Else(
                hdmiext_audio_clk.eq(0),
                audio_counter.eq(audio_counter + 1),
            ),
        ]
        
        next_adr = Signal(30) # wishbone!
        sample_cnt = Signal(16)
        cur_buf = Signal(1)
        next_buf = Signal(1)

        self.comb += [
            self.bufstatus.fields.buffer_num.eq(cur_buf),
            self.bufstatus.fields.buffer_left.eq(sample_cnt),
        ]

        need_data = Signal()
        # self-reset need_data, whenever we consume a sample in hdmi (audio_clk) we request more
        self.sync += [
            If(~need_data & hdmiext_audio_clk,
               need_data.eq(1),
            )
        ]
        # autostop
        self.sync += [
            If((sample_cnt == 0) & self.ctrl.fields.autostop & hdmiext_audio_clk, # we just consumed the last sample in autostop mode
               self.ctrl.we.eq(1),
               self.ctrl.dat_w.eq(self.ctrl.storage & 0xFFFFFEFF), # reset 'play'
            ).Else(
                self.ctrl.we.eq(0),
            ),
        ]
        
        self.submodules.play_fsm = play_fsm = FSM(reset_state="Reset")
        play_fsm.act("Reset",
                    NextState("Silent")
        )
        play_fsm.act("Silent",
                     NextValue(hdmiext_audio_word_0, 0),
                     NextValue(hdmiext_audio_word_1, 0),
                     If(self.ctrl.fields.play,
                        NextValue(cur_buf, self.ctrl.fields.buffer_num),
                        NextValue(next_buf, self.ctrl.fields.buffer_num + 1),
                        NextValue(need_data, 1),
                        Case(self.ctrl.fields.buffer_num, {
                            0x0: [
                                NextValue(next_adr, self.buf0_addr.storage[2:32]),
                                NextValue(sample_cnt, self.buf0_size.fields.size),
                            ],
                            0x1: [
                                NextValue(next_adr, self.buf1_addr.storage[2:32]),
                                NextValue(sample_cnt, self.buf1_size.fields.size),
                            ],
                        }),
                        NextState("Play"),
                     )
        )
        play_fsm.act("Play",
                     If(~self.ctrl.fields.play,
                        NextValue(hdmiext_audio_word_0, 0),
                        NextValue(hdmiext_audio_word_1, 0),
                        NextState("Silent"),
                     ).Elif((sample_cnt == 0), # ran out of sample in this buffer
                            set_irq.eq(self.irqctrl.fields.irq_enable), # transient notify to the host we emptied a buffer # only raised when enabled
                            If(~self.ctrl.fields.autostop,
                               NextValue(cur_buf, next_buf),
                               NextValue(next_buf, next_buf + 1),
                               Case(next_buf, {
                                   0x0: [
                                       NextValue(next_adr, self.buf0_addr.storage[2:32]),
                                       NextValue(sample_cnt, self.buf0_size.fields.size),
                                   ],
                                   0x1: [
                                       NextValue(next_adr, self.buf1_addr.storage[2:32]),
                                       NextValue(sample_cnt, self.buf1_size.fields.size),
                                   ],
                               }),
                            )
                            # stay in "Play"
                     )
        )
        led0 = soc.platform.request("user_led", 0)
        led1 = soc.platform.request("user_led", 1)
        self.comb += [
            self.bufstatus.fields.play.eq(play_fsm.ongoing("Play")),
            #led0.eq(play_fsm.ongoing("Play")),
            led0.eq(self.buf_desc.fields.signedness),
            led1.eq(self.buf_desc.fields.mono),
        ]

        # intermediate storage when playing less than stereo 16-bits
        
        nextSample = Signal(24)

        # auto-reload
        self.submodules.req_fsm = req_fsm = FSM(reset_state="Reset")
        req_fsm.act("Reset",
                    NextState("Idle")
        )
        req_fsm.act("Idle",
                    If(need_data & self.ctrl.fields.play & play_fsm.ongoing("Play") & (sample_cnt != 0),
                       NextValue(busmaster.cyc, 1),
                       NextValue(busmaster.stb, 1),
                       NextValue(busmaster.sel, 2**len(busmaster.sel)-1),
                       NextValue(busmaster.we, 0),
                       NextValue(busmaster.adr, next_adr),
                       If(~self.buf_desc.fields.width,
                          NextState("WaitForAck16")
                       ).Else(
                           NextState("WaitForAck8")
                       ),
                    ),
        )
        req_fsm.act("WaitForAck16",
                    If(busmaster.ack,
                       NextValue(busmaster.cyc, 0),
                       NextValue(busmaster.stb, 0),
                       If(~self.buf_desc.fields.mono,
                          NextValue(hdmiext_audio_word_0, Cat(busmaster.dat_r[ 8:16], busmaster.dat_r[ 0: 8])),
                          NextState("Idle"),
                       ).Else(
                           NextValue(hdmiext_audio_word_0, Cat(busmaster.dat_r[24:32], busmaster.dat_r[16:24])),
                           NextValue(nextSample[ 0:24], busmaster.dat_r[ 0:24]), # only 16 are needed, what's most efficient ?
                           NextState("SecondSample16"),
                       ),
                       NextValue(hdmiext_audio_word_1, Cat(busmaster.dat_r[24:32], busmaster.dat_r[16:24])),
                       NextValue(next_adr, next_adr + 1),
                       NextValue(sample_cnt, sample_cnt - 1),
                       NextValue(need_data, 0), # this will self-reset to 1 above after the next audio_clk cycle, i.e. when hdmi consume the data
                    )
        )
        req_fsm.act("SecondSample16",
                    If(~self.ctrl.fields.play | ~play_fsm.ongoing("Play") | (sample_cnt == 0),
                       NextState("Idle"),
                    ).Elif(need_data,
                           NextValue(hdmiext_audio_word_0, Cat(nextSample[ 8:16], nextSample[ 0: 8])),
                           NextValue(hdmiext_audio_word_1, Cat(nextSample[ 8:16], nextSample[ 0: 8])),
                           NextValue(sample_cnt, sample_cnt - 1),
                           NextValue(need_data, 0), # this will self-reset to 1 above after the next audio_clk cycle, i.e. when hdmi consume the data
                           NextState("Idle"),
                    )
        )

        offset8bits = 7 # by how many bits to shift 8-bits audio to create 16-bits ; 0 to 8 
        
        req_fsm.act("WaitForAck8",
                    If(busmaster.ack,
                       NextValue(busmaster.cyc, 0),
                       NextValue(busmaster.stb, 0),
                       If(~self.buf_desc.fields.mono,
                          NextValue(hdmiext_audio_word_0, Cat(Replicate(0, offset8bits),
                                                              busmaster.dat_r[16:24],
                                                              Replicate(~self.buf_desc.fields.signedness & busmaster.dat_r[23], 8-offset8bits)) -
                                                          Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                       ).Else(
                           NextValue(hdmiext_audio_word_0, Cat(Replicate(0, offset8bits),
                                                               busmaster.dat_r[24:32],
                                                               Replicate(~self.buf_desc.fields.signedness & busmaster.dat_r[31], 8-offset8bits)) -
                                                           Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                       ),
                       NextValue(hdmiext_audio_word_1, Cat(Replicate(0, offset8bits),
                                                           busmaster.dat_r[24:32],
                                                           Replicate(~self.buf_desc.fields.signedness & busmaster.dat_r[31], 8-offset8bits)) -
                                                       Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                       NextValue(nextSample[ 0:24], busmaster.dat_r[ 0:24]), # only 16 are needed if ~mono, what's more efficient ?
                       NextValue(next_adr, next_adr + 1),
                       NextValue(sample_cnt, sample_cnt - 1),
                       NextValue(need_data, 0), # this will self-reset to 1 above after the next audio_clk cycle, i.e. when hdmi consume the data
                       NextState("SecondSample8"),
                    )
        )
        req_fsm.act("SecondSample8",
                    If(~self.ctrl.fields.play | ~play_fsm.ongoing("Play") | (sample_cnt == 0),
                       NextState("Idle"),
                    ).Elif(need_data,
                           If(~self.buf_desc.fields.mono,
                              NextValue(hdmiext_audio_word_0, Cat(Replicate(0, offset8bits),
                                                                  nextSample[ 0: 8],
                                                                  Replicate(~self.buf_desc.fields.signedness & nextSample[ 7], 8-offset8bits)) -
                                                              Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                              NextValue(hdmiext_audio_word_1, Cat(Replicate(0, offset8bits),
                                                                  nextSample[ 8:16],
                                                                  Replicate(~self.buf_desc.fields.signedness & nextSample[15], 8-offset8bits)) -
                                                              Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                              NextState("Idle"),
                           ).Else(
                              NextValue(hdmiext_audio_word_0, Cat(Replicate(0, offset8bits),
                                                                  nextSample[16:24],
                                                                  Replicate(~self.buf_desc.fields.signedness & nextSample[ 7], 8-offset8bits)) -
                                                              Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                              NextValue(hdmiext_audio_word_1, Cat(Replicate(0, offset8bits),
                                                                  nextSample[16:24],
                                                                  Replicate(~self.buf_desc.fields.signedness & nextSample[15], 8-offset8bits)) -
                                                              Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                              NextState("ThirdSample8"),
                           ),
                           NextValue(sample_cnt, sample_cnt - 1),
                           NextValue(need_data, 0), # this will self-reset to 1 above after the next audio_clk cycle, i.e. when hdmi consume the data
                    )
        )
        req_fsm.act("ThirdSample8",
                    If(~self.ctrl.fields.play | ~play_fsm.ongoing("Play") | (sample_cnt == 0),
                       NextState("Idle"),
                    ).Elif(need_data,
                           # mono only here
                           NextValue(hdmiext_audio_word_0, Cat(Replicate(0, offset8bits),
                                                               nextSample[ 8:16],
                                                               Replicate(~self.buf_desc.fields.signedness & nextSample[ 7], 8-offset8bits)) -
                                                           Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                           NextValue(hdmiext_audio_word_1, Cat(Replicate(0, offset8bits),
                                                               nextSample[ 8:16],
                                                               Replicate(~self.buf_desc.fields.signedness & nextSample[15], 8-offset8bits)) -
                                                           Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                           NextState("FourthSample8"),
                           NextValue(sample_cnt, sample_cnt - 1),
                           NextValue(need_data, 0), # this will self-reset to 1 above after the next audio_clk cycle, i.e. when hdmi consume the data
                    )
        )
        req_fsm.act("FourthSample8",
                    If(~self.ctrl.fields.play | ~play_fsm.ongoing("Play") | (sample_cnt == 0),
                       NextState("Idle"),
                    ).Elif(need_data,
                           # mono only here
                           NextValue(hdmiext_audio_word_0, Cat(Replicate(0, offset8bits),
                                                               nextSample[ 0: 8],
                                                               Replicate(~self.buf_desc.fields.signedness & nextSample[ 7], 8-offset8bits)) -
                                                           Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                           NextValue(hdmiext_audio_word_1, Cat(Replicate(0, offset8bits),
                                                               nextSample[ 0: 8],
                                                               Replicate(~self.buf_desc.fields.signedness & nextSample[15], 8-offset8bits)) -
                                                           Cat(Replicate(0, 7+offset8bits), self.buf_desc.fields.signedness, Replicate(0, 8-offset8bits))), # fixme: endianess
                           NextState("Idle"),
                           NextValue(sample_cnt, sample_cnt - 1),
                           NextValue(need_data, 0), # this will self-reset to 1 above after the next audio_clk cycle, i.e. when hdmi consume the data
                    )
        )
