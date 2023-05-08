#!/bin/bash

GERBER_FILES="PI2PMODSPI-B_Cu.gbr PI2PMODSPI-B_Mask.gbr PI2PMODSPI-B_Paste.gbr PI2PMODSPI-B_SilkS.gbr PI2PMODSPI-Edge_Cuts.gbr PI2PMODSPI-F_Cu.gbr PI2PMODSPI-F_Mask.gbr PI2PMODSPI-F_Paste.gbr PI2PMODSPI-F_SilkS.gbr"

POS_FILES="PI2PMODSPI-top.pos"

DRL_FILES="PI2PMODSPI-NPTH.drl PI2PMODSPI-PTH.drl PI2PMODSPI-PTH-drl_map.ps PI2PMODSPI-NPTH-drl_map.ps"

FILES="${GERBER_FILES} ${POS_FILES} ${DRL_FILES} top.pdf PI2PMODSPI.d356 PI2PMODSPI.csv"

echo $FILES

KICAD_PCB=PI2PMODSPI.kicad_pcb

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

zip PI2PMODSPI.zip $FILES
