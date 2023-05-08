#!/bin/bash

GERBER_FILES="FLASHTEMP-B_Cu.gbr FLASHTEMP-B_Mask.gbr FLASHTEMP-B_Paste.gbr FLASHTEMP-B_SilkS.gbr FLASHTEMP-Edge_Cuts.gbr FLASHTEMP-F_Cu.gbr FLASHTEMP-F_Mask.gbr FLASHTEMP-F_Paste.gbr FLASHTEMP-F_SilkS.gbr"

POS_FILES="FLASHTEMP-top.pos"

DRL_FILES="FLASHTEMP-NPTH.drl FLASHTEMP-PTH.drl FLASHTEMP-PTH-drl_map.ps FLASHTEMP-NPTH-drl_map.ps"

FILES="${GERBER_FILES} ${POS_FILES} ${DRL_FILES} top.pdf FLASHTEMP.d356 FLASHTEMP.csv"

echo $FILES

KICAD_PCB=FLASHTEMP.kicad_pcb

ABORT=no
for F in $FILES; do 
    if test \! -f $F || test $KICAD_PCB -nt $F; then
	echo "Regenerate file $F"
	ABORT=yes
    fi
done

if test $ABORT == "yes"; then
    exit -1;
fi

zip FLASHTEMP.zip $FILES
