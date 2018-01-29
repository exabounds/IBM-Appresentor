
"""
 * (C) Copyright IBM Corporation 2017
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *    IBM Algorithms & Machines team
"""

import os.path as path                   # handling the paths
import sys                               # for exiting the script
import inspect                           # for retrieving the position of the 
import pprint                            # pretty printing stuff
import copy                              # to perform a deep copy of the translator
import itertools                         # for the combination generations
import random
import pprint

import pyDOE as doe



def build_doe_space(optimizations, build_input, run_input, omp_threads, mpi_procs, data_dimension):
	"""
	This function merge the different parameters of an experiment
	in a single array in preparation of a doe plan

	Parameters:
		- optimizations:   dictionary that represents the optimizations
		                    -key: the name of the optimization
		                    -value: a list of the possible values of the optimization
		- build_input:     dictionary that represents the build input
		                    -key: the name of the iput
		                    -value: a list of the possible values of the input
		- run_input:       dictionary that represents the execution input
		                    -key: the name of the iput
		                    -value: a list of the possible values of the input
		- omp_threads:     a list of the possible values for the parallelization
		- mpi_procs:       a list of the possible values for the mpi processes
		- data_dimension:  an int, the maximum data dimension of the application (for tiling)

	Return:
		- a list of list that merges all the possible parameters values made like that
		     [ [1, 2, 4],  ['max', 'none', ...], ...]
		       ---------   --------------------
		          op1                opt2

		- a dictionary that translate from the name of the input to the index in the parameters array
		    { 'optimizations' : {'opt1' : 0, 'opt2' : 1},
		      'build_input'   : {'flag1': 2, 'flag2': 3},
		      'run_input'     : {'flag1': 4, 'flag2': 5},
		      'omp_threads'   : {'omp'  : 6},
		      'mpi_procs'     : {'mpi'  : 7} }
	"""

	# initial declarations
	parameters = []
	translator = {}
	index_counter = 0


	# take into account the tile dimensions over the input data dimension
	tile_values = list(optimizations['tile'])
	del optimizations['tile']
	tileL2_values = list(optimizations['tileL2'])
	del optimizations['tileL2']
	for d in range(data_dimension):
		optimizations['tile_d{0}'.format(d)] = tile_values
		optimizations['tileL2_d{0}'.format(d)] = tileL2_values


	# start with the optimization flags
	translator['optimizations'] = {}
	for opt_name in optimizations:
		parameters.append(optimizations[opt_name])
		translator['optimizations'][opt_name] = index_counter
		index_counter += 1

  # TODO: What if here I check the options and if it is MPI (or OMP), I just duplicate the MPI index in the translator?
	# continue with the build input flags
	translator['build_input'] = {}
	for flag_name in build_input:
		parameters.append(build_input[flag_name])
		translator['build_input'][flag_name] = index_counter
		index_counter += 1

	# continue with the run input flags
	translator['run_input'] = {}
	for flag_name in run_input:
		parameters.append(run_input[flag_name])
		translator['run_input'][flag_name] = index_counter
		index_counter += 1

	# continue with the openMP flags
	translator['omp_threads'] = {}
	if omp_threads:
		parameters.append(omp_threads)
		translator['omp_threads']['omp'] = index_counter
		index_counter += 1

	# stop with the MPI flags
	translator['mpi_procs'] = {}
	if mpi_procs:
		parameters.append(mpi_procs)
		translator['mpi_procs']['mpi'] = index_counter

	return parameters, translator






def value_to_flag_translation(run, translator):
	"""
	This function translate the values of the flags in the
	given run accordingly to the script usage.

	Parameter:
		- run:        a list of string that represents the parameters value
		- translator: the translator dictionary generated by build_doe_space

	Return:
		- make_args:    the string that describes the make arguments
		- exe_args:     the string that describes the exection flags
		- openmp_flag:  the string that set the OMP thread #
		- mpi_command:  the string that describes the mpi/openmp commands, it is
		                meant to be used as an application prefix
		- name1:        a compact name with only the building information
		- name2:        a compact name with all the run information
	"""

	##############   compose the make arguments
	make_args = ''
	name1 = ''

	### Get the optimization flags
	opt_args = 'OPTIMIZATION_FLAGS="'

	# take care of the tiling dimension thing
	translator_temp = copy.deepcopy(translator)
	tile_dict = {}
	eviction_list = []
	for opt in translator_temp['optimizations']:
		if 'tileL2' in opt:
			d_index = opt[8:]
			tile_dict[d_index] = run[translator_temp['optimizations'][opt]]
			eviction_list.append(opt)
	for e in eviction_list:
		del translator_temp['optimizations'][e]
	tile = ['' for x in tile_dict]
	for t in tile_dict:
		tile[int(t)] = tile_dict[t]
	if tile:
		opt_args = '{0}--tileL2 {1} '.format(opt_args, ','.join(tile))
	name1 = '{0}_tileL2-{1}_'.format(name1, '.'.join(tile))
	tile_dict = {}
	eviction_list = []
	for opt in translator_temp['optimizations']:
		if 'tile' in opt:
			d_index = opt[6:]
			tile_dict[d_index] = run[translator_temp['optimizations'][opt]]
			eviction_list.append(opt)
	for e in eviction_list:
		del translator_temp['optimizations'][e]
	tile = ['' for x in tile_dict]
	for t in tile_dict:
		tile[int(t)] = tile_dict[t]
	if tile:
		opt_args = '{0}--tile {1} '.format(opt_args, ','.join(tile))
	name1 = '{0}_tile-{1}_'.format(name1, '.'.join(tile))

	# take care of the others optimization flags
	for opt in translator_temp['optimizations']:
		opt_args = '{0}--{1} {2} '.format(opt_args, opt, run[translator_temp['optimizations'][opt]])
		name1 = '{0}_{1}-{2}_'.format(name1, opt, run[translator_temp['optimizations'][opt]])

	# update the make arguments
	make_args = '{0}" '.format(opt_args[:-1])


	### Get the input flags
	for inp in translator_temp['build_input']:
		make_args = '{0} {1}={2}'.format(make_args, inp, run[translator_temp['build_input'][inp]])
		name1 = '{0}_{1}-{2}_'.format(name1, inp, run[translator_temp['build_input'][inp]])




	##############   compose the exec arguments
	exe_args = ''
	name2 = '{0}'.format(name1)
	for exc in translator_temp['run_input']:
		exe_args = '{0} {1} {2}'.format(exe_args, exc, run[translator_temp['run_input'][exc]])
		name2 = '{0}_{1}-{2}_'.format(name2, exc, run[translator_temp['run_input'][exc]])



	##############   compose the openmp command
	openmp_flag = ''
	if translator_temp['omp_threads']:
		openmp_flag = 'env OMP_NUM_THREADS={0}'.format(run[translator_temp['omp_threads']['omp']])
		name2 = '{0}_OMP-{1}_'.format(name2, run[translator_temp['omp_threads']['omp']])


	##############   compose the mpi command
	mpi_command = ''
	if translator_temp['mpi_procs']:
		mpi_command = 'mpirun -np {0} '.format(run[translator_temp['mpi_procs']['mpi']])
		name2 = '{0}_NPC-{1}_'.format(name2, run[translator_temp['mpi_procs']['mpi']])




	# print('|||||||||||||||||||||||||||||||||||||||||||||||||||||||||')
	# print('MAKE_ARGS={0}'.format(make_args))
	# print('EXE_ARGS={0}'.format(exe_args))
	# print('OPENMP_FLAG={0}'.format(openmp_flag))
	# print('MPI_COMMAND={0}'.format(mpi_command))
	# print('NAME1={0}'.format(name1))
	# print('NAME2={0}'.format(name2))
	# print('|||||||||||||||||||||||||||||||||||||||||||||||||||||||||')

	return make_args, exe_args, openmp_flag, mpi_command, name1, name2






def generate_makefile(makefile, plan, app_folder, benchmark):
	"""
	This function write the application makefile that
	actually execute the experiments

	Parameters:
		-makefile:  a file descriptor of the makefile
		-plan:      the execution plan autogenerated
		-folder:    the path of the experiment
		-app_folder:the path of the application source
	"""

	# get the self location
	self_location = path.abspath(path.realpath(path.split(inspect.getfile( inspect.currentframe() ))[0]))

	# write the header
	makefile.write('.PHONY: clean all isolate generate.cnls experiments.cnls \n')
	makefile.write('.PRECIOUS: %profile\n\n')
	
	makefile.write('PROFILER?=myProfile\n')
	makefile.write('MPIHOSTSFLAG?=\n\n')

	# write the all command
	makefile.write('all: isolate generate.cnls experiments.cnls\n')

	# write the isolate command
	build_paths = [path.join('.', plan[x][0][3], 'Makefile') for x in plan]
	makefile.write('isolate:\\\n{0}'.format('  \\\n'.join(build_paths)))
	makefile.write('\n\n\n\n\n')

	# write the generate command
	plain_exe = [path.join('.', plan[x][0][3], 'application.exe') for x in plan]
	cinstrumented_exe = [path.join('.', plan[x][0][3], 'application.cnls') for x in plan]
	makefile.write('generate.cnls:\\\n{0}'.format('  \\\n'.join(plain_exe)))
	makefile.write('  \\\n')
	makefile.write('  \\\n'.join(cinstrumented_exe))
	makefile.write('\n\n\n\n\n')

	# write the profile instrumented command
	experiments_path = []
	for build in plan:
		for e in plan[build]:
			experiments_path.append(path.join('.', e[3], e[4]))
	required_prefiles = ['{0}.cnls.rawprofile'.format(x) for x in experiments_path]
	makefile.write('experiments.cnls:\\\n{0}'.format('  \\\n'.join(required_prefiles)))
	makefile.write('\n\n\n\n\n')
	
	# write the profile non-instrumented command
	experiments_path = []
	for build in plan:
		for e in plan[build]:
			experiments_path.append(path.join('.', e[3], e[4]))
	required_times = ['{0}.time'.format(x) for x in experiments_path]
	makefile.write('runnative:\\\n{0}'.format('  \\\n'.join(required_times)))
	makefile.write('\n\n\n\n\n')

	# generate the recipe for the forlder
	for p in plan:
		makefile.write('{0}:\n'.format(path.join('.', plan[p][0][3], 'Makefile')))
		makefile.write('\t@$(MAKE) -C {0} isolate {1} ISOLATED_BUILD_DIR=$(abspath ./{2})\n\n'.format(app_folder, p, plan[p][0][3]))
	makefile.write('\n\n\n\n\n')

#	# generate the recipe for the main.bc files
#	for p in plan:
#		makefile.write('{0}: {1}\n'.format(path.join('.', plan[p][0][3], 'main.bc'), path.join('.', plan[p][0][3], 'Makefile')))
#		makefile.write('\t@$(MAKE) -C {0} main.bc\n\n'.format(path.join('.', plan[p][0][3])))

	# generate the recipe for generating the coupled instrumented executables
	for p in plan:
		makefile.write('{0}: {1} \n'.format(path.join('.', plan[p][0][3], 'application.cnls'), path.join('.', plan[p][0][3], 'Makefile') ))
		makefile.write('\t@$(MAKE) -C {0} application.cnls TEST_NAME="{1}"\n\n'.format(path.join('.', plan[p][0][3]), plan[p][0][3]))

	# generate the recipe for generating the executables
	for p in plan:
		makefile.write('{0}: {1} \n'.format(path.join('.', plan[p][0][3], 'application.exe'), path.join('.', plan[p][0][3], 'Makefile') ))
		makefile.write('\t@$(MAKE) -C {0} exe_plain\n\n'.format(path.join('.', plan[p][0][3])))
	makefile.write('\n\n\n\n\n')


	# generate the recipe for generating the coupled rawprofiles and times
	for index_build, p in enumerate(plan):
		for index_run, e in enumerate(plan[p]):
			makefile.write('{0}: {1}\n'.format(path.join('.', e[3],'{0}.cnls.rawprofile'.format(e[4])), path.join('.', e[3], 'application.cnls')))
			makefile.write('\t@echo "\\tRUN\\tEXE {0}/{1}"\n'.format(index_run + index_build + 1, len(plan[p]) + len(plan) - 1))
			makefile.write('\t@{0} --out {1} --application {2} --benchmark {3} {4}\n'.format(path.join('..', '..','..','..','scripts', 'pisa_script_generator'), path.join('.', e[3], '{0}.header.json'.format(e[4])), app_folder.split('/')[-2], benchmark, path.join('.', e[3], '{0}.cnls.rawprofile'.format(e[4]))))
			makefile.write('\t@RUNTIMEARGS=\"{0}\" OMPENVSETTING=\"{1}\" MPIEXECUTIONCOMMAND=\"{2}\" make -C {3} {4}.cnls.rawprofile\n'.format(e[0],e[1],e[2],e[3],e[4])  )
	makefile.write('\n\n\n\n\n')
			
	# generate the recipe for generating the times
	for index_build, p in enumerate(plan):
		for index_run, e in enumerate(plan[p]):
			makefile.write('{0}: {1}\n'.format(path.join('.', e[3], '{0}.time'.format(e[4])), path.join('.', e[3], 'application.exe')))
			makefile.write('\t@echo "\\tRUN\\tNLS {0}/{1}"\n'.format(index_run + index_build + 1, len(plan[p]) + len(plan) - 1))
			makefile.write('\t@PROFILER=$(PROFILER) RUNTIMEARGS=\"{0}\" OMPENVSETTING=\"{1}\" MPIEXECUTIONCOMMAND=\"{2}\" make -C {3} {4}.time\n'.format(e[0],e[1],e[2],e[3],e[4]) )
	makefile.write('\n\n\n\n\n')

	# generate the recipe for plotting the results
	makefile.write('plot:\n')
	makefile.write('\t@{0} --out . .\n'.format(path.join('..', '..','..','..','scripts', 'plot_experiment')))
	makefile.write('\n\n\n\n\n')	


	# generate the clean command
	makefile.write('clean:\n')
	for p in plan:
		makefile.write('\trm -r -f {0}\n'.format(path.join('.', plan[p][0][3])))







def plackett_burmann(parameters, translator, tile_fixed_values):
	"""
	This function generates the doe plan for the experiment. If a parameters
	has more than two values, this function takes the first and the last
	elements.

	Parameters:
		- parameters:      the list of parameters generated by build_doe_space
		- translator:      the translator dictionary generated by build_doe_space
		- tile_same_value: if True, than the tiling value is propagated on all the dimensions

	Return:
		- the plan of the execution composed as a dictionary:
			keys: the name of the application build
			values: a list of tuples, where each tuple represents a single experiment
	"""

	# enforce that all the parameters have at most two levels
	for index, p in enumerate(parameters):
		if len(p) > 2:
			parameters[index] = [p[0], p[-1]]

	# count how many parameters have two levels
	dynamic_parameters = []
	constant_parameters = []
	for index, p in enumerate(parameters):
		if len(p) == 2:
			dynamic_parameters.append(index)
		else:
			constant_parameters.append(index)

	# prune the tile space
	constrained_parameters = {}
	for tile_p in tile_fixed_values:
		try:
			# consider the case where the tile size is fixed
			value = int(tile_fixed_values[tile_p])
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constant_parameters.append(translator['optimizations'][tile_p])
				parameters[translator['optimizations'][tile_p]] = [value]

		except ValueError:
			# consider the case where the tile value depends on another tile
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constrained_parameters[tile_p] = translator['optimizations'][tile_fixed_values[tile_p]]



	# generate the experiment matrix
	experiments = doe.pbdesign(len(dynamic_parameters))

	# compose the plan
	plan = {}
	for e  in experiments:

		# get the value of all the dynamic values
		values = {}
		for index, v in enumerate(e):
			real_index = dynamic_parameters[index]
			if v == -1:
				values[real_index] = str(parameters[real_index][0])
			elif v == 1:
				values[real_index] = str(parameters[real_index][1])


		# add back the tile values
		for tile_p in constrained_parameters:
			values[translator['optimizations'][tile_p]] = values[constrained_parameters[tile_p]]

		# add the constants
		for c in constant_parameters:
			values[c] = str(parameters[c][0]) # TODO: MPIbuild, take from MPI ?
			if values[c] == 'omp_threads':
				values[c] = values[translator['omp_threads']['omp']]
			if values[c] == 'mpi_procs':
				values[c] = values[translator['mpi_procs']['mpi']]

		# create the run list with the right values
		run = ['' for x in values]
		for key in values:
			run[int(key)] = values[key]


		# perform the flag translation
		make_args, exe_args, openmp_flag, mpi_command, name1, name2 = value_to_flag_translation(run, translator)
		# add it to the plan
		try:
			plan[make_args].append((exe_args, openmp_flag, mpi_command, name1, name2))
		except KeyError as itsok:
			plan[make_args] = [(exe_args, openmp_flag, mpi_command, name1, name2)]
		except:
			raise

		print('\n')

	# return the plan
	return plan



def two_level_full_factorial(parameters, translator, tile_fixed_values):
	"""
	This function generates the doe plan for the experiment using a simple
	full-factorial design

	Parameters:
		- parameters: the list of parameters generated by build_doe_space
		- translator: the translator dictionary generated by build_doe_space

	Return:
		- the plan of the execution composed as a dictionary:
			keys: the name of the build
			values: a list of tuples, where each tuple represents a single experiment
	"""

	# enforce that all the parameters have at most two levels
	for index, p in enumerate(parameters):
		if len(p) > 2:
			parameters[index] = [p[0], p[-1]]

	# count how many parameters have two levels
	dynamic_parameters = []
	constant_parameters = []
	for index, p in enumerate(parameters):
		if len(p) == 2:
			dynamic_parameters.append(index)
		else:
			constant_parameters.append(index)

	# prune the tile space
	constrained_parameters = {}
	for tile_p in tile_fixed_values:
		try:
			# consider the case where the tile size is fixed
			value = int(tile_fixed_values[tile_p])
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constant_parameters.append(translator['optimizations'][tile_p])
				parameters[translator['optimizations'][tile_p]] = [value]

		except ValueError:
			# consider the case where the tile value depends on another tile
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constrained_parameters[tile_p] = translator['optimizations'][tile_fixed_values[tile_p]]



	# generate the experiment matrix
	experiments = doe.ff2n(len(dynamic_parameters))

	# compose the plan
	plan = {}
	for e  in experiments:

		# get the value of all the dynamic values
		values = {}
		for index, v in enumerate(e):
			real_index = dynamic_parameters[index]
			if v == -1:
				values[real_index] = str(parameters[real_index][0])
			elif v == 1:
				values[real_index] = str(parameters[real_index][1])

		# add back the tile values
		for tile_p in constrained_parameters:
			values[translator['optimizations'][tile_p]] = values[constrained_parameters[tile_p]]

		# add the constants
		for c in constant_parameters:
			values[c] = str(parameters[c][0]) # TODO: MPIbuild, take from MPI ?
			if values[c] == 'omp_threads':
				values[c] = values[translator['omp_threads']['omp']]
			if values[c] == 'mpi_procs':
				values[c] = values[translator['mpi_procs']['mpi']]

		# create the run list with the right values
		run = ['' for x in values]
		for key in values:
			run[int(key)] = values[key]


		# perform the flag translation
		make_args, exe_args, openmp_flag, mpi_command, name1, name2 = value_to_flag_translation(run, translator)

		# add it to the plan
		try:
			plan[make_args].append((exe_args, openmp_flag, mpi_command, name1, name2))
		except KeyError as itsok:
			plan[make_args] = [(exe_args, openmp_flag, mpi_command, name1, name2)]
		except:
			raise

	# return the plan
	return plan


def exhaustive(parameters, translator, tile_fixed_values):
	"""
	This function generates the doe plan for the experiment using of the whole design space

	Parameters:
		- parameters: the list of parameters generated by build_doe_space
		- translator: the translator dictionary generated by build_doe_space

	Return:
		- the plan of the execution composed as a dictionary:
			keys: the name of the build
			values: a list of tuples, where each tuple represents a single experiment
	"""

	# do not enforse constraints on parameter levels

	# count how many parameters have at least two levels
	dynamic_parameters = []
	constant_parameters = []
	levels = []
	for index, p in enumerate(parameters):
		if len(p) >= 2:
			dynamic_parameters.append(index)
			levels.append(len(p))
		else:
			constant_parameters.append(index)

	# prune the tile space
	constrained_parameters = {}
	for tile_p in tile_fixed_values:
		try:
			# consider the case where the tile size is fixed
			value = int(tile_fixed_values[tile_p])
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constant_parameters.append(translator['optimizations'][tile_p])
				parameters[translator['optimizations'][tile_p]] = [value]

		except ValueError:
			# consider the case where the tile value depends on another tile
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constrained_parameters[tile_p] = translator['optimizations'][tile_fixed_values[tile_p]]



	# generate the experiment matrix
	experiments = doe.fullfact(levels)

	# compose the plan
	plan = {}
	for e  in experiments:

		# get the value of all the dynamic values
		values = {}
		for index, v in enumerate(e):
			real_index = dynamic_parameters[index]
			values[real_index] = str(parameters[real_index][int(v)])

		# add back the tile values
		for tile_p in constrained_parameters:
			values[translator['optimizations'][tile_p]] = values[constrained_parameters[tile_p]]

		# add the constants
		for c in constant_parameters:
			values[c] = str(parameters[c][0]) # TODO: MPIbuild, take from MPI ?
			if values[c] == 'omp_threads':
				values[c] = values[translator['omp_threads']['omp']]
			if values[c] == 'mpi_procs':
				values[c] = values[translator['mpi_procs']['mpi']]

		# create the run list with the right values
		run = ['' for x in values]
		for key in values:
			run[int(key)] = values[key]


		# perform the flag translation
		make_args, exe_args, openmp_flag, mpi_command, name1, name2 = value_to_flag_translation(run, translator)

		# add it to the plan
		try:
			plan[make_args].append((exe_args, openmp_flag, mpi_command, name1, name2))
		except KeyError as itsok:
			plan[make_args] = [(exe_args, openmp_flag, mpi_command, name1, name2)]
		except:
			raise

	# return the plan
	return plan





def central_composite(parameters, translator, tile_fixed_values):
	"""
	This function generates the doe plan for the experiment.

	Parameters:
		- parameters: the list of parameters generated by build_doe_space
		- translator: the translator dictionary generated by build_doe_space

	Return:
		- the plan of the execution composed as a dictionary:
			keys: the name of the application build
			values: a list of tuples, where each tuple represents a single experiment
	"""

	# enforce that all the parameters have at least 5 levels
	for index, p in enumerate(parameters):

		# we assume that the first five value are for training
		if len(p) > 5:
			parameters[index] = [ p[0], p[1], p[2], p[3], p[4] ]

		# fix the input for fewer values
		if len(p) == 4:
			parameters[index] = [ p[0], p[1], p[2], p[3], p[3] ]
		if len(p) == 3:
			parameters[index] = [ p[0], p[0], p[1], p[2], p[2] ]
		if len(p) == 2:
			parameters[index] = [ p[0], p[0], p[0], p[1], p[1] ]



	# count how many parameters have two levels
	dynamic_parameters = []
	constant_parameters = []
	for index, p in enumerate(parameters):# NOTE: if I only give the option OMP or MPI as value, this will be a constant parameter
		if len(p) == 1:
			constant_parameters.append(index) 
		else:
			dynamic_parameters.append(index)


	# prune the tile space
	constrained_parameters = {}
	for tile_p in tile_fixed_values:
		try:
			# consider the case where the tile size is fixed
			value = int(tile_fixed_values[tile_p])
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constant_parameters.append(translator['optimizations'][tile_p])
				parameters[translator['optimizations'][tile_p]] = [value]

		except ValueError:
			# consider the case where the tile value depends on another tile
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constrained_parameters[tile_p] = translator['optimizations'][tile_fixed_values[tile_p]]



	# generate the experiment matrix
	experiments_suggested = list(doe.ccdesign(len(dynamic_parameters))) # TODO: should MPIbuild end up in constant because it only have a single possible value: MPI ?
	experiments = []
	for e_proposed in experiments_suggested:
		is_ok = True
		for e_accepted in experiments:
			equal = True
			for index, element in enumerate(e_accepted):
				if e_proposed[index] != element:
					equal = False
					break
			if equal:
				is_ok = False
				break
		if is_ok:
			experiments.append(e_proposed)

	# compose the plan
	plan = {}
	for e  in experiments:

		# get the value of all the dynamic values
		values = {}
		for index, v in enumerate(e):
			real_index = dynamic_parameters[index]
			if v < -1:
				values[real_index] = str(parameters[real_index][0])
			elif v == -1:
				values[real_index] = str(parameters[real_index][1])
			elif v == 0:
				values[real_index] = str(parameters[real_index][2])
			elif v == 1:
				values[real_index] = str(parameters[real_index][3])
			elif v > 1:
				values[real_index] = str(parameters[real_index][4])

		# add back the tile values
		for tile_p in constrained_parameters:
			values[translator['optimizations'][tile_p]] = values[constrained_parameters[tile_p]]


		# add the constants
		for c in constant_parameters:
			values[c] = str(parameters[c][0]) # TODO: MPIbuild, take from MPI ?
			if values[c] == 'omp_threads':
				values[c] = values[translator['omp_threads']['omp']]
			if values[c] == 'mpi_procs':
				values[c] = values[translator['mpi_procs']['mpi']]

		# create the run list with the right values
		run = ['' for x in values]
		for key in values:
			run[int(key)] = values[key]


		# perform the flag translation
		make_args, exe_args, openmp_flag, mpi_command, name1, name2 = value_to_flag_translation(run, translator)

		# add it to the plan
		try:
			plan[make_args].append((exe_args, openmp_flag, mpi_command, name1, name2))
		except KeyError as itsok:
			plan[make_args] = [(exe_args, openmp_flag, mpi_command, name1, name2)]
		except:
			raise

	# return the plan
	return plan





def latin_square(parameters, translator, tile_fixed_values):
	"""
	This function generates the doe plan for the experiment.

	Parameters:
		- parameters: the list of parameters generated by build_doe_space
		- translator: the translator dictionary generated by build_doe_space

	Return:
		- the plan of the execution composed as a dictionary:
			keys: the name of the application build
			values: a list of tuples, where each tuple represents a single experiment
	"""

	# enforce that all the parameters have the same number of parameter
	min_param_num = min(len(x) for x in parameters if len(x) > 1)
	param_changed = 0
	for index, p in enumerate(parameters):
		# if the parameter has more parameters, cut them off
		if len(p) > min_param_num:
			parameters[index] = p[:min_param_num]
			param_changed += 1
	if param_changed:
		print('[WARNING] Taken the first {0} values from {1} parameter(s)'.format(min_param_num, param_changed))


	# count how many parameters have two levels
	dynamic_parameters = []
	constant_parameters = []
	for index, p in enumerate(parameters):
		if len(p) == 1:
			constant_parameters.append(index)
		else:
			dynamic_parameters.append(index)


	# prune the tile space
	constrained_parameters = {}
	for tile_p in tile_fixed_values:
		try:
			# consider the case where the tile size is fixed
			value = int(tile_fixed_values[tile_p])
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constant_parameters.append(translator['optimizations'][tile_p])
				parameters[translator['optimizations'][tile_p]] = [value]

		except ValueError:
			# consider the case where the tile value depends on another tile
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constrained_parameters[tile_p] = translator['optimizations'][tile_fixed_values[tile_p]]



	# generate the experiment matrix
	experiments = doe.lhs(len(dynamic_parameters), samples=min_param_num, criterion='maximin')

	# compose the plan
	plan = {}
	for e  in experiments:

		# get the value of all the dynamic values
		values = {}
		delta_increment = 1.0 / float(min_param_num)
		for index, v in enumerate(e):
			real_index = dynamic_parameters[index]
			value_index = int(v / delta_increment)
			values[real_index] = parameters[real_index][value_index]

		# add back the tile values
		for tile_p in constrained_parameters:
			values[translator['optimizations'][tile_p]] = values[constrained_parameters[tile_p]]


		# add the constants
		for c in constant_parameters:
			values[c] = str(parameters[c][0]) # TODO: MPIbuild, take from MPI ?
			if values[c] == 'omp_threads':
				values[c] = values[translator['omp_threads']['omp']]
			if values[c] == 'mpi_procs':
				values[c] = values[translator['mpi_procs']['mpi']]

		# create the run list with the right values
		run = ['' for x in values]
		for key in values:
			run[int(key)] = values[key]


		# perform the flag translation
		make_args, exe_args, openmp_flag, mpi_command, name1, name2 = value_to_flag_translation(run, translator)

		# add it to the plan
		try:
			plan[make_args].append((exe_args, openmp_flag, mpi_command, name1, name2))
		except KeyError as itsok:
			plan[make_args] = [(exe_args, openmp_flag, mpi_command, name1, name2)]
		except:
			raise

	# return the plan
	return plan





def random_doe(parameters, translator, tile_fixed_values, number_sample=250):
	"""
	This function generates the doe plan for the experiment.

	Parameters:
		- parameters: the list of parameters generated by build_doe_space
		- translator: the translator dictionary generated by build_doe_space

	Return:
		- the plan of the execution composed as a dictionary:
			keys: the name of the application build
			values: a list of tuples, where each tuple represents a single experiment
	"""

	# count how many parameters have two levels
	dynamic_parameters = []
	constant_parameters = []
	for index, p in enumerate(parameters):
		if len(p) == 1:
			constant_parameters.append(index)
		else:
			dynamic_parameters.append(index)


	# prune the tile space
	constrained_parameters = {}
	for tile_p in tile_fixed_values:
		try:
			# consider the case where the tile size is fixed
			value = int(tile_fixed_values[tile_p])
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constant_parameters.append(translator['optimizations'][tile_p])
				parameters[translator['optimizations'][tile_p]] = [value]

		except ValueError:
			# consider the case where the tile value depends on another tile
			if translator['optimizations'][tile_p] in dynamic_parameters:
				dynamic_parameters.remove(translator['optimizations'][tile_p])
				constrained_parameters[tile_p] = translator['optimizations'][tile_fixed_values[tile_p]]



	# generate the experiment matrix
	experiments = []
	loop_watchdog = number_sample * 100
	while (len(experiments) < number_sample) and (loop_watchdog > 0):
		run = [random.choice(parameters[param_index]) for param_index in dynamic_parameters]
		good = True
		for e in experiments:
			equal = True
			for index, element in enumerate(e):
				if run[index] != element:
					equal = False
					break
			if equal:
				good = False
				break
		if good:
			experiments.append(run)
		loop_watchdog -= 1

	# compose the plan
	plan = {}
	for e  in experiments:

		# get the value of all the dynamic values
		values = {}
		for index, v in enumerate(e):
			real_index = dynamic_parameters[index]
			values[real_index] = v

		# add back the tile values
		for tile_p in constrained_parameters:
			values[translator['optimizations'][tile_p]] = values[constrained_parameters[tile_p]]


		# add the constants
		for c in constant_parameters:
			values[c] = str(parameters[c][0]) # TODO: MPIbuild, take from MPI ?
			if values[c] == 'omp_threads':
				values[c] = values[translator['omp_threads']['omp']]
			if values[c] == 'mpi_procs':
				values[c] = values[translator['mpi_procs']['mpi']]

		# create the run list with the right values
		run = ['' for x in values]
		for key in values:
			run[int(key)] = values[key]


		# perform the flag translation
		make_args, exe_args, openmp_flag, mpi_command, name1, name2 = value_to_flag_translation(run, translator)

		# add it to the plan
		try:
			plan[make_args].append((exe_args, openmp_flag, mpi_command, name1, name2))
		except KeyError as itsok:
			plan[make_args] = [(exe_args, openmp_flag, mpi_command, name1, name2)]
		except:
			raise

	# return the plan
	return plan