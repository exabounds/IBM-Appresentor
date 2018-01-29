At some point the toolchain has been used to investigate polyhedral optiomizations.
Later, this activity has been dropped. There are still some scripts that may
ease future reintregration effort if the idea will be of interest. Pluto is the
LLVM tool implementing the polyhedral optimization. Following some description
on the scripts used.

######## Script meaning

experiment_generator  -> Generate an experiment
doe_common            -> Dependence of the generator script
pisa_script_generator -> Generate the JSON information to define the scaling parameters
plot_experiment       -> Plot the result of an experiment
pluto_expander        -> Copy the expanded loop in the original source file
pluto_flaggy          -> Manage the appropriate flag between pluto, opt and clang
pluto_opt             -> Wrapper for the pluto optimizer to handle the pluto errors
pluto_postprocessor   -> Fix some problems in the pluto sorce file

All the scripts are used whitin the toolchain and it isn't required to call them
explicitly. The only exception is the script that generates the experiments.
In any case all the scripts provides an help message that describes how to use them.

####### Experiment generation

The workflow is explained in the main README file. This section explains how to
change the design space for the experiment.

The file that must be edited is "experiment_generator". In particular the focus is
between lines 29-81.

In particular the dictionary "optimizations" defines the optimization supported by
the toolchain.
These are all the available options:
  --tile          -> The list of all the required size of the first level of tiling
                        - "none" : the pluto optimizer is not called
                        - any number: the tile size, the number are coma separated
  --tileL2        -> The list of all the required size of the second level of tiling
  --fusion        -> Defines the level of instruction fusion in the scope, the
                     available values are:
                        - "none": the instructions are not fused
                        - "smart": the instructions are fused using a pluto heuristic
                        - "max": the instructions are fused whenever it is possible
  --unrolling     -> Handle the loop unrolling factor, the available values are:
                        - "none": the loop unrolling is disabled
                        - "auto": the unrolling factor is set automatically by opt
                        - any number: force the unroll factor for all the loops
  --vectorization -> Handle the the loop and instructions vetorization, the available
                     values are:
                        - "none": to disable the loop vectorization
                        - "auto": let opt to automatically vectorize the code
                        - any number: force the vector depth whenever possible
  --parallel      -> If its value is "auto", pluto automatically parallelize the
                     application scop, using the #pragma omp parallel for

The default value for all the optimizations is "none", explicetely turning down
all these optimizations.






The list "omp_threads" state the number of OMP thread to be used in the experiment.
This is being done, setting the enviroment variable OMP_NUM_THREADS trhough the env
command, for each run of the experiment.






The list "mpi_procs" state the number of MPI processes to be used in the experiment.
If the array is empty, it means that the application does not support MPI.






The dictionary "tile_fixed_values" is used to fix some parameters of the experiment.
Since the number of parameters that influence the tile depends on the number of
input of the application, using this dictionary is possible to fix them after that
all the parameters are evluated.
The key of the dictionary is the parameter object of the constraint. If the value is
a number, then the parameter value is fixed to that value. If the value is a string,
then the script handle the value as a name of another parameter. In this way it is
possible to assign the value of the object parameter using another one as reference.
In the toolchain it is used the convention of enumerating the parameters that
influence the tile or the 2nd level tiling in this way:

 tile_d0, tile_d1, tile_d2, ..., tile_dn
 tileL2_d0, tileL2_d1, tileL2_d2, ...., tileL2_dn

where n is the number of the dimension of the tile.







The function "filter_input" is meant to be used to filter out the value for the
input for each application that compose the benchmark. In order to write a
fileter is required to change the body of the function.
For instance in this way it is selected only the first input for each application:

# used to filter out the amount of input level for each application
def filter_input(build_input, run_input):
	"""
	Used to alter the input of the single application.

	Parameter:
		- build_input: dictionary of compile-time flags
		- run_input:   dicotionary of run-time flags

	Note:
	Both the dictionary have this shape:
	*_input = {
		'FLAG_NAME_1'    : ['VALUE1', 'VALUE2', ...],
		'FLAG_NAME_2'    : ['VALUE1', 'VALUE2', ...],
		...
	}
	"""

	# take a single value for the input
	for input_name in build_input:
		if len(build_input[input_name]) > 1:
			new_values = [build_input[input_name][0]]
			del build_input[input_name]
			build_input[input_name] = list(new_values)

	# take a signle value for the input
	for input_name in run_input:
		if len(run_input[input_name]) > 1:
			new_values = [run_input[input_name][0]]
			del run_input[input_name]
			run_input[input_name] = list(new_values)

	return build_input, run_input




