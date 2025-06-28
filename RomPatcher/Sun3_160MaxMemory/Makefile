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

all: sun3-carrera-rev-3.0.bin

show: rompatch.elf
	$(NM) $< | sort

sun3-carrera-rev-3.0.bin: ../ rompatch.raw input.txt
	/bin/cp ../sun3-carrera-rev-3.0.bin sun3-carrera-rev-3.0.bin
	${PATCHER} -i rompatch.raw -p sun3-carrera-rev-3.0.bin -d input.txt

linker.ld: input.txt rompatch.s
	${GENLINK} -d $< >| $@
	echo $(shell for X in `grep .section rompatch.s | awk '{ print $$2 }' `; do grep -q $$X linker.ld || echo " $$X has no entry in linker.ld" && /bin/false; done)

rompatch.o: rompatch.s
	${AS} ${ARCHFLAGS} $< -o $@ -a > rompatch.l

rompatch.elf: linker.ld rompatch.o ${CSRC:.c=.o} # linker script must be first
	${LD} -o $@ -T $^

rompatch.raw: rompatch.elf
	${OBJCOPY} $^ $@ --input-target=elf32-m68k --output-target=binary

clean:
	rm -f res.inc ${CSRC_ASM} *.o rompatch.srec rompatch.raw rompatch.dir rompatch.l linker.ld rompatch.elf
