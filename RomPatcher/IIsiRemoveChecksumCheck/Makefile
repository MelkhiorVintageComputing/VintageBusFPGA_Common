RETRO68=/home/dolbeau/Retro68/build/toolchain
AS=${RETRO68}/bin/m68k-apple-macos-as
CC=${RETRO68}/bin/m68k-apple-macos-gcc
LD=${RETRO68}/bin/m68k-apple-macos-ld
STRIP=${RETRO68}/bin/m68k-apple-macos-strip
OBJCOPY=${RETRO68}/bin/m68k-apple-macos-objcopy
NM=${RETRO68}/bin/m68k-apple-macos-nm

HOSTCC=gcc
HOSTCFLAGS=-O2

ARCHFLAGS=-march=68020 -mcpu=68020
CFLAGS=-O2 -mpcrel

GENLINK=../patcher/genlink
PATCHER=../patcher/patcher

all: IIsi.ROM

show: rompatch.elf
	$(NM) $< | sort

IIsi.ROM: ../IIsi.ROM rompatch.raw input.txt
	/bin/cp ../IIsi.ROM IIsi.ROM
	${PATCHER} -i rompatch.raw -p IIsi.ROM -d input.txt

linker.ld: input.txt rompatch.s
	${GENLINK} -d $< >| $@
	$(shell for X in `grep .section rompatch.s | awk '{ print $$2 }' `; do grep -q $$X linker.ld || echo " $$X has no entry in linker.ld" && /bin/false; done)

rompatch.o: rompatch.s
	${AS} ${ARCHFLAGS} $< -o $@ -a > rompatch.l

rompatch.elf: linker.ld rompatch.o ${CSRC:.c=.o} # linker script must be first
	${LD} -o $@ -T $^

rompatch.raw: rompatch.elf
	${OBJCOPY} $^ $@ --input-target=elf32-m68k --output-target=binary

clean:
	rm -f res.inc ${CSRC_ASM} *.o rompatch.srec rompatch.raw rompatch.dir rompatch.l VidRom*.s
