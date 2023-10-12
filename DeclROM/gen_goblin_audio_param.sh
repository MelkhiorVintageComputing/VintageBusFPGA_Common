#!/bin/bash

/bin/rm -f goblin_param.inc

touch goblin_param.inc

echo -n 'csr_goblin_base = ' >> goblin_param.inc

grep -q csr_base,goblin ../../csr.csv || echo "0x0" >> goblin_param.inc
grep csr_base,goblin ../../csr.csv | awk -F, '{ print $3}' | sed -e 's/0x[fF]0a0/0x00a0/' >> goblin_param.inc

echo 'goblin_audiobuffer_offset = 0x00920000' >> goblin_param.inc
echo 'goblin_audiobuffer_size = 0x00002000' >> goblin_param.inc
