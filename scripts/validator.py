#!/usr/bin/env python
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

#################################
###### Import section
#################################
import argparse                          # processing the input
import os.path as path                   # handling the paths
import os                                # for creating the path
import errno                             # for checking before creating a path
import sys                               # for exiting the script
import subprocess                        # for calling commands
import shutil                            # for copying files
import inspect                           # for retrieving the position of the script
import pprint                            # for pretty printing the name of the 
import time                              # for the name of the folder
import itertools                         # for the combination generations
import pprint                            # pretty printer for debug




#################################
###### Utility functions
#################################


def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc: # Python >2.5
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else: raise



def value2name(what, none_is_actually_a_size = False):
	if what == 0:
		return 'none'
	if what == 1:
		if not none_is_actually_a_size:
			return 'smart'
	if what == 2:
		if not none_is_actually_a_size:
			return 'max'
	if what == -1:
		return 'auto'
	return str(int(what))



def param2flags(parameters):

	# declare the optimization flag
	flags = []



	# compose the tiling
	values = {}
	tile_flag = ''
	for p in parameters:
		if 'tile' in p and 'tileL2' not in p:
			values[int(p[5:])] = int(parameters[p])
	tile_value = ''
	for v in range(len(values)):
		tile_value = '{0},{1}'.format(tile_value, value2name(values[v], none_is_actually_a_size=True))
	if tile_value:
		tile_value = tile_value[1:]
		tile_flag = '--tile {0}'.format(tile_value)



	# compose the L2 tiling
	values = {}
	tileL2_flag = ''
	for p in parameters:
		if 'tileL2' in p:
			values[int(p[7:])] = int(parameters[p])
	tile_valueL2 = ''
	for v in range(len(values)):
		tile_valueL2 = '{0},{1}'.format(tile_valueL2, value2name(values[v], none_is_actually_a_size=True))
	if tile_valueL2:
		tile_valueL2 = tile_valueL2[1:]
		tileL2_flag = '--tileL2 {0}'.format(tile_valueL2)




	# compose the loop unrolling
	unrolling_factor = ''
	for p in parameters:
		if 'unrolling' == p:
			unrolling_factor = '--unrolling {0}'.format(str(int(parameters[p])))




	# compose the fusion policy
	fusion_policy = ''
	for p in parameters:
		if 'fusion' == p:
			fusion_policy = '--fusion {0}'.format(value2name(parameters[p]))



	# compose the automatic parallelization
	parallel_auto = ''
	for p in parameters:
		if 'parallel' == p:
			parallel_auto = '--parallel {0}'.format(value2name(parameters[p]))


	# compose the vectorization
	vectorization = ''
	for p in parameters:
		if 'vectorization' == p:
			vectorization = '--vectorization {0}'.format(value2name(parameters[p]))




	# compose the optimization flags
	flags.append('OPTIMIZATION_FLAGS={0} {1} {2} {3} {4}'.format(tile_flag, tileL2_flag, unrolling_factor, fusion_policy, parallel_auto, vectorization))


	# compose the remainder of the flag
	for p in parameters:

		# filter in the actual parameters
		if not (('tile' in p) or ('unrolling' in p) or ('fusion' in p) or ('estimanteExTime' in p) or ('estimatedExTimeModelFromPrunedDOE' in p) or ('parallel' in p) or ('OMP' in p) or ('vectorization' in p)):

			# otherwise compose the value
			flags.append('{0}={1}'.format(p, str(int(parameters[p]))))


	# return the list of flags and the number of OpenMP processes
	return flags, int(parameters['OMP'])















if __name__ == "__main__":

	# obtain the required path
	self_location = path.abspath(path.realpath(path.split(inspect.getfile( inspect.currentframe() ))[0]))
	results_location = path.abspath(path.realpath(path.join(path.split(inspect.getfile( inspect.currentframe() ))[0], "../results")))

	# parse the input arguments
	arg_parser = argparse.ArgumentParser(description='Utility application that generates the experiments to validate the predictions')
	arg_parser.add_argument('--version', action='version', version='0.1a', help='print the version of the program and exit')
	arg_parser.add_argument('--name', dest='app_name', type=str, help='the name of the executable')
	arg_parser.add_argument('--iteration', dest='n', default=1, type=int, help='the number of times an experiment is repeated')
	arg_parser.add_argument('--source', dest='src', type=str, default=os.getcwd(), help='the path to the application makefile')
	arg_parser.add_argument('predition', type=str, help='the path to the prediction file')
	args = arg_parser.parse_args()



	################################################################## parse the cvs file
	predictions = []
	header = {}
	with open(os.path.realpath(args.predition), 'r') as f:
		for line in f:

			# define the single configuration
			point = {}

			# parse the line
			new_line = line.replace('\n', '')
			parsed_line = new_line.split('\t')

			# -------  parse the data line
			if header:
				for field_name in header:
					point[field_name] = float(parsed_line[header[field_name]])
				predictions.append(point)
			else:
				for index_column, meaning in enumerate(parsed_line):
					header[meaning.replace("\r", "").replace("\n", "")] = index_column



	################################################################## create the results folder
	folder_path = path.abspath(path.realpath(os.path.join(os.getcwd(), 'out')))
	mkdir_p(folder_path)






	################################################################## perform the validation

	# get the current directory
	working_path = path.abspath(path.realpath(os.getcwd()))

	# observed performance
	observations = []

	# get the name of the profile file
	file_name = os.path.join(path.abspath(path.realpath(args.src)), 'profile.time')

	# loop over the predicted runs
	for p in predictions:

		# create the same configuration
		configuration = {}
		for field_name in header:
			configuration[field_name] = p[field_name]

		# get the list of flag values and the number of threads
		compile_flags, omp_num = param2flags(configuration)

		# clean the directory
		pwdSee = ['pwd']
		pwdProc = subprocess.Popen(pwdSee)
		pwdProc.wait()
		command = ['make', 'clean']
		make = subprocess.Popen(command, cwd=args.src)
		make.wait()


		# compile the application
		command = ['make']
		command.extend(compile_flags)
		make = subprocess.Popen(command, cwd=args.src)
		make.wait()


		# perform the experiment more than once
		exec_times = []
		for i in range(args.n):

			# run the application
			command = ['/home/dgadioli/toolchain/bin/profile', 'env OMP_NUM_THREADS={0} {1}'.format(int(configuration['OMP']), os.path.join(os.path.realpath(args.src), args.app_name)), '"{0}"'.format(file_name)]
			print('Running the application with "{0}" and {1} OMP threads'.format(' '.join(compile_flags), int(configuration['OMP'])))
			print(command)
			print(args.src)
			application = subprocess.Popen(command, cwd=args.src)
			application.wait()
	
			# read the time file
			execution_time = -1
			with open(file_name, 'r') as f:
				for line in f:
					execution_time = float(line)
			print('OBSERVED EXECUTION TIME: {0}'.format(execution_time))

			if not (i == 0 and args.n > 1):
				exec_times.append(execution_time)
	
			# remove the file
			os.remove(file_name)
	
		# add the observation
		observation = []
		for field_name in header:
			observation.append(p[field_name])
		observation.append(str(float(sum(exec_times)) / float(len(exec_times))))
		observations.append(observation)


	# print the observed dse
	with open('observed_dse.data', 'w') as f:
		for h in header:
			f.write('{0}\t'.format(h))
		f.write('observedExTime')
		f.write('\n')
		for o in observations:
			for data in o:
				f.write('{0}\t'.format(data))
			f.write('\n')





