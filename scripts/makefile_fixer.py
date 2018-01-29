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
import sys                               # for exiting the script
import os                                # for retrieving the current working directory
import subprocess                        # for calling commands
import shutil                            # for copying files
import argparse                          # run time flag handler
import errno                             # retrieve the errornumber meaning




class Application:
	"""
	 path          ->   the path of the configuration
	 profile_name  ->   the name of the profile
	 build_flags   ->   the flags used to compile the application
	 omp           ->   the omp number
	"""

	def __init__(self, profile_path):

		# get the path of the configuration
		self.path = './{0}'.format(os.path.basename(os.path.dirname(profile_path)))
		self.profile_name = os.path.basename(profile_path)

		# get the configuration as path
		configuration_coded = os.path.splitext(os.path.basename(profile_path))[0]

		# split configuration by elements
		elements = [x for x in configuration_coded.split('_') if x ]

		# declare the configurations
		optimization_elements = []
		build_elements = []
		self.omp = '1'

		# reconstruct the configuration
		for element in elements:

			# split the name from the value
			name, value = element.split('-')

			# parse the tile
			if name == 'tile' or name == 'tileL2':
				optimization_elements.append('--{0} {1}'.format(name, value.replace('.',',')))
				continue

			# parse the other optimizations
			if name in ['parallel', 'fusion', 'vectorization', 'unrolling']:
				optimization_elements.append('--{0} {1}'.format(name, value))
				continue

			# parse the remainder of the build flags
			if name != 'OMP':
				build_elements.append('{0}={1}'.format(name, value))
			else:
				self.omp = value

		# build the compile flag
		build_elements.append('OPTIMIZATION_FLAGS="{0}"'.format(' '.join(optimization_elements)))
		self.build_flags = '{0}'.format(' '.join(build_elements))


	def __eq__(self, other):
		return self.path == other.path


	def __hash__(self):
		return hash(self.path)


	def __str__(self):
		return('+++++\n{0}\n{1}\n{2}\n++++'.format(self.path, self.build_flags, self.omp))







def get_pisa_profiles(where):
	# retrieve all the time files from the experiments
	data_files = []
	for dirpath, dirnames, filenames in os.walk(os.path.abspath(os.path.realpath(where))):
		data_files.extend([os.path.join(dirpath, x) for x in filenames if x.endswith('.rawprofile')])

	# safe check
	if not data_files:
		#print('PLOT: Unable to find any profile files, aborting...')
		sys.exit(os.EX_NOINPUT)

	return data_files






if __name__ == "__main__":

	arg_parser = argparse.ArgumentParser(description='print the global Makefile of an experiment')
	arg_parser.add_argument('--application_build_path', type=str, default='/home/dgadioli/toolchain/benchmarks/polybench3.2/01.correlation/src')
	arg_parser.add_argument('--application_name', type=str, default='01.correlation')
	arg_parser.add_argument('--benchmark_name', type=str, default='polybench3.2')
	arg_parser.add_argument('experiment', type=str, nargs='?', default=os.getcwd(), help='the root path of the experiment')
	args = arg_parser.parse_args()

	# get the position of the root directory
	root_dir = os.path.abspath(os.path.realpath(args.experiment))


	# get all the directory that compose the experiment
	configurations_file = get_pisa_profiles(root_dir)

	# reconstruct the application configuration
	confs = []
	for c in configurations_file:
		confs.append(Application(c))


	# print the header
	print('.PHONY: clean isolate generate experiments compress convert')
	print('all: isolate generate experiments')


	################ print the dependencies for the commands
	
	print('isolate:\\')
	deps = set('{0}/Makefile \\'.format(c.path) for c in confs)
	for d in deps:
		print(d)
	print('\n\n')


	print('generate:\\')
	deps_exe = set('{0}/application.exe \\'.format(c.path) for c in confs)
	deps_cnls = set('{0}/application.cnls \\'.format(c.path) for c in confs)
	deps = deps_cnls.union(deps_exe)
	for d in deps:
		print(d)
	print('\n\n')


	print('experiments:\\')
	deps = set('{0}/{1} \\'.format(c.path, c.profile_name) for c in confs)
	for d in deps:
		print(d)
	print('\n\n')


	print('compress:\\')
	deps = set('{0}/application.tar.gz \\'.format(c.path) for c in confs)
	for d in deps:
		print(d)
	print('\n\n')


	print('convert:\\')
	deps = set('{0}/{1} \\'.format(c.path, c.profile_name.replace('rawprofile', 'profile')) for c in confs)
	for d in deps:
		print(d)
	print('\n\n')




	################ print the actual rule to generate the experiments

	# generate the isolate rules
	deps = set('{0}/Makefile:'.format(c.path) for c in confs)
	for d in deps:
		for c in confs:
			if c.path in d:
				build_flags = c.build_flags
				path =  c.path
				break
		print(d)
		print('\t@$(MAKE) -C {0} isolate {1} ISOLATED_BUILD_DIR=$(abspath {2})'.format(args.application_build_path, build_flags, path))
		print()


	# generate the main.bc files
	deps = set(c for c in confs)
	for c in deps:
		print('{0}/main.bc: {0}/Makefile'.format(c.path))
		print('\t@$(MAKE) -C {0} main.bc'.format(c.path))
		print()


	# generate the application.cnls
	for c in deps:
		print('{0}/application.cnls: {0}/main.bc {0}/Makefile'.format(c.path))
		print('\t@$(MAKE) -C {0} exe_instrumented TEST_NAME="{0}"'.format(c.path))
		print()


	# generate the application.exe
	for c in deps:
		print('{0}/application.exe: {0}/main.bc {0}/Makefile'.format(c.path))
		print('\t@$(MAKE) -C {0} exe_plain'.format(c.path))
		print()


	# generate the rawprofile
	num = len(confs)
	for index, c in enumerate(confs):
		print('{0}/{1}: {0}/application.cnls'.format(c.path, c.profile_name))
		print('\t@echo "\\tRUN\\tNLS {0}/{1}"'.format(index+1, num))
		print('\t@env OMP_NUM_THREADS={0} $<  2> $@'.format(c.omp))
		print()


	# convert the profile
	for c in confs:
		print('{0}/{1}:'.format(c.path, c.profile_name.replace('rawprofile', 'profile')))
		print('\t@echo "\\tCONVERTING PROFILE"')
		print('\t@../../../../scripts/pisa_script_generator --out {0}/converter.R --application {1} --benchmark {2} {0}/{3}'.format(c.path, args.application_name, args.benchmark_name, c.profile_name))
		print('\t@Rscript {0}/converter.R'.format(c.path))
		print()


	# compress the executable
	for c in deps:
		print('{0}/application.tar.gz: {0}/Makefile'.format(c.path, c.profile_name))
		print('\t@$(MAKE) -C {0} compress'.format(c.path))
		print()


	# clean command
	print('clean:')
	for c in deps:
		print('\t@rm -r -f {0}'.format(c.path))
	print()