# RomPatcher

This is a small set of tools to help with ROM patching. A single input file made up of lines \<address\>,\<size\>,\<name\> describes which area need patching. <size> can be 0 for e.g. calls to exsiting functions.

One tool generates linked file to place things where they need to be in the compiled binary.
One tool  copies the relevant area from the generated binary to the file that needs to be patched.

An assembly source file can then be used to write the patch, placing code in the appropriate sections as per the linker file. They are then patched into the final file.

Example:
* IIsiRemoveChecksumCheck: replace a few instructions in a Macintosh IIsi ROM file to disable the checksum test (thus allowing further patching)
* IIsiExtraMemoryi: patch the memory chunk table and some code to enable an extra area of memory in a IIsi ROM, usable with e.g. the IIsiFPGA
