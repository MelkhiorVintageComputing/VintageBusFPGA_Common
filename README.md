# VintageBusFPGA_Common
Common stuff for SBusFPGA, NuBusFPGA, ...

## Content

* goblin_fb.py: 'Goblin', a Framebuffer (bit-mapped graphic display), supporting 1/2/4/8/16/32 bit depth, a single hardwired resolution to the screen, and windowboxed lower resolution. Also uses fb_dma.py (to read the framebuffer content from a LiteDRAM controller) and fb_video.py (timing generator). Originally based on Litex's own framebuffer code.

* goblin_accel.py: acceleration engine for the 'Goblin' framebuffer. Basically a custom VexRiscv core (VexRiscv_GoblinAccel_NuBus.v or VexRiscv_GoblinAccel_SBus.v) and some firmware (the blit_goblin*.* files).

* cdc_wb.py: a custom wrapper around (https://github.com/alexforencich/verilog-wishbone/blob/master/rtl/wb_async_reg.v)[alexforencich's wb_async_reg.v], a Wishbone DCD component. Feature a customizable time-out to avoir the fast side overloading the slow side (a bit hackish but it works for my use case).

* fpga_blk_dma.py: a block DMA between a LIteSDRAM port and a set of FIFOs. Used to create burst (SBus) or block (NUbus) accesses from the device to the host memory. Used by RAM-based "disks".

* wb_master.py: A small Wishbone master (originally from enjoy-gigital) that can do basic read/write/wait commands. Used to configure the DDR3 controller w/o firmware.
