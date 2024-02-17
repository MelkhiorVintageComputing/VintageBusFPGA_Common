#!/bin/bash

/bin/rm -f liteeth_param.inc

touch liteeth_param.inc

echo -n 'liteethmac_base = ' >> liteeth_param.inc
grep -q csr_base,ethmac ../../csr.csv || echo "0x0" >> liteeth_param.inc
grep csr_base,ethmac ../../csr.csv | awk -F, '{ print $3}' | sed -e 's/0x[fF]0a0/0x00a0/' >> liteeth_param.inc

echo -n 'liteethphy_base = ' >> liteeth_param.inc
grep -q csr_base,ethphy ../../csr.csv || echo "0x0" >> liteeth_param.inc
grep csr_base,ethphy ../../csr.csv | awk -F, '{ print $3}' | sed -e 's/0x[fF]0a0/0x00a0/' >> liteeth_param.inc

echo -n 'liteethmac_memory = ' >> liteeth_param.inc
grep -q memory_region,ethmac ../../csr.csv || echo "0x0" >> liteeth_param.inc
grep memory_region,ethmac ../../csr.csv | awk -F, '{ print $3}' | sed -e 's/0x[fF]0c0/0x00c0/' >> liteeth_param.inc
