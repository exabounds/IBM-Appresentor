#!/bin/bash
curl -O https://asc.llnl.gov/CORAL-benchmarks/Throughput/lulesh2.0.3.tgz
tar xzvf lulesh2.0.3.tgz
mv Makefile README TODO lulesh-comm.cc lulesh-init.cc lulesh-util.cc lulesh-viz.cc lulesh.cc lulesh.h lulesh_tuple.h CORAL/lulesh/src
rm lulesh2.0.3.tgz
mv CORAL/lulesh/src/Makefile CORAL/lulesh/src/Makefile.original
cp CORAL/Makefile.lulesh CORAL/lulesh/src/Makefile
