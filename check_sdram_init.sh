#!/bin/bash

GOODPHY=`grep csr_base,ddrphy csr.csv | awk -F, '{ print $3 }'`
GOODSDRAM=`grep csr_base,sdram csr.csv | awk -F, '{ print $3 }'`

USEPHY=`grep ddrphy_base *soc.py | awk '{ print $3 }' | sed -e 's/,.*//'`
USESDRAM=`grep sdram_dfii_base *soc.py | awk '{ print $3 }' | sed -e 's/,.*//'`

RET=0

if test $GOODPHY != $USEPHY; then
    echo "WARNING WARNING WARNING PHY has wrong CSR base in SDRAM initilizer WARNING WARNING WARNING"
    RET=-1
fi
if test $GOODSDRAM != $USESDRAM; then
    echo "WARNING WARNING WARNING PHY has wrong CSR base in SDRAM initilizer WARNING WARNING WARNING"
    RET=-1
fi

exit $RET

