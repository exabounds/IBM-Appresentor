# IBM-Appresentor

The _IBM Exascale Extrapolator_ (part of the [_IBM ExaBounds_](https://github.com/exabounds/IBM-ExaBounds/) distribution) scales software profiles to a target scale, e.g., exascale. It takes as input a set of software profiles representative of a parameter space, the input parameters of the profiled software. The parameter sets for those profiles must be generated according to a [design of experiments](https://en.wikipedia.org/wiki/Design_of_experiments).

The _IBM Appresentor_ in this repository automates this design of experiments and kicks off profiling runs with [_IBM Platform-Independent Software Analysis_](https://github.com/exabounds/ibm-pisa), generating the complete set of profiles required as an input to the _IBM Exascale Extrapolator_.

To get started, please refer to the [documentation](https://github.com/exabounds/IBM-Appresentor/blob/master/Documentation/Manual.pdf).

More information on the context of this tool can be found at the [_Algorithms & Machines_](http://researcher.watson.ibm.com/researcher/view_group.php?id=6395) project page at at _IBM Research – Zurich_.
