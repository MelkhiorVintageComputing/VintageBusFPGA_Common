# 3/160 expanded memory ROM patch

This small patch enables the Sun 3/160 memory to recongnize more than 32 MiB of RAM (only tested in TME, The Machine Emulator)

* "replace1" patches the upper bound of the memory-sizing loop
* "replace2" patches an assumption at one point in the ROM that only 32 MiB is installed. The original test is to check for >=32 MiB and if so, subtract 128 KiB. This replaces the subtraction with a hardwired (32MiB - 128 KiB) value.

The combinations of both patches is enough that 128 MiB of memory can be specified in the TME config file:
`ram0 at obmem0 addr 0x0: tme/host/posix/memory ram 128MB`
And both the ROM and NetBSD (tested 9.0) will recognize 128 MiB.