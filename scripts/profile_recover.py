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



optimizations = ['tile', 'unrolling', 'vectorization', 'fusion', 'parallel', 'OMP', 'NPC']


instrumentation_values = {
  'WINDOW_SIZE'            :  'inf',#'54',
  'DATA_CACHE_LINE_SIZE'   :  'inf',#'128',
  'INST_CACHE_LINE_SIZE'   :  'inf',#'16',
  'INST_SIZE'              :  'inf'#'1'
}


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


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



def name2value(what, none_is_actually_a_size = False):
	if what == 'none':
		if none_is_actually_a_size:
			return '1'
		else:
			return '0'
	if what == 'auto':
		return '-1'
	if what == 'smart':
		return '1'
	if what == 'max':
		return '2'
	try:
		return str(int(what))
	except:
		return str(what)


def name2Params(name):
	answer = {}
	tokens = name.split('_')
	for t in tokens:

		# skip empty tokens
		if not t:
			continue

		# split the name from the value
		param_name, param_value = t.split('-')

		# check if we need to disable pluto
		if 'tile' in param_name:
			enable_this_tiling_level = False
			tile_values = param_value.split('.')
			for t_temp in tile_values:
				if t_temp != 'none':
					enable_this_tiling_level = True


		# handle the tiling thing
		if param_name == 'tile':
			if not enable_this_tiling_level:
				tile_values = ['0' for x in tile_values]
			for index, value in enumerate(tile_values):
				answer['tileD{0}'.format(index)] = name2value(value, True)

		# handle the tilingL2 thing
		if 'tileL2' == param_name:

			# check if the first level of tiling is enabled
			for t2 in tokens:
				if not t2:
					continue
				name1, value1 = t2.split('-')
				if name1 == 'tile':
					enable_pluto = False
					for t_temp in tile_values:
						if t_temp != 'none':
							enable_pluto = True
							break
					if not enable_pluto:
						enable_this_tiling_level = False

			if not enable_this_tiling_level:
				tile_values = ['0' for x in tile_values]
			for index, value in enumerate(tile_values):
				answer['tileL2D{0}'.format(index)] = name2value(value)

		# process the remainder of the parameters
		if (not 'tile' == param_name) and (not 'tileL2' == param_name):
			name, value = t.split('-')
			answer[name] = name2value(value)

	return answer



def convert_and_copy(in_file, out_file, application, benchmark):

	# find the parameters name
	parameters = name2Params(os.path.splitext(os.path.basename(in_file))[0])

	# find all the optimization and input tokens
	opt_flags = {}
	input_flags = {}
	global optimizations
	for p in parameters:
		for o in optimizations:
			if o in p:
				opt_flags[p] = parameters[p]
			else:
				input_flags[p] = parameters[p]

	# create the R script
	with open('convert.R','w') as f:
	
		# write the first part of the script
		f.write('library(jsonlite)\nmergeToJSON <- function() {\n')
		f.write('  data <- fromJSON("{0}")\n  outputFile <- "{1}"\n'.format(in_file, out_file))
		f.write('  if (file.exists(outputFile))\n    file.remove(outputFile)\n')
		f.write('  JSONelements <- list()\n  JSONelements[["application"]] <- "{0}"\n'.format(application))
		f.write('  JSONelements[["benchmark"]]   <- "{0}"\n'.format(benchmark))
	
	
		# write the application scale
		f.write('JSONelements[["appScale"]]    <- list(\n')
		scaling_factors = []
		for p in parameters:
			scaling_factors.append('                                      {0}={1}'.format(p, parameters[p]))
		f.write(",\n".join(scaling_factors))
		f.write('\n                                     )\n')
	
		# write the application configuration
		f.write('JSONelements[["appConfig"]]   <- list(testFile="NA",\n                                        exeCommand=data$swProperties$execmd,\n')
		f.write('                                        compilerOptimization="')
		optimizations = []
		for o in opt_flags:
		  optimizations.append('{0}={1}'.format(o, opt_flags[o]))
		f.write(','.join(optimizations))
	
	
		# write the remainder of the configuration script
		f.write("""",
		                                    ilpCtrlSerialized="disabled",
		                                    branchEntropyAll="no",
		                                    branchEntropyCond="no",
		                                    libraryCommit="ca6cd215c1243ce53c4dd59f5ed09498f4550a59")
	    
	  JSONelements[["time"]]        <- paste(sep='','',Sys.time())
	  JSONelements[["threads"]]     <- list()
	    
	  count <- 1
	  
	  for(thread in data$swProperties$threads$`thread_id`) {
	      crtThread <- list()
	      
	      crtThread[["threadId"]]             <- data[[1]]$threads$`thread_id`[count]
	      crtThread[["processId"]]            <- data[[1]]$threads$`processor_id`[count]
	      crtThread[["instructionMix"]]       <- as.list(data[[1]]$threads$instructionMix[count,])  
	      crtThread[["openMPinstructionMix"]] <- as.list(data[[1]]$threads$openMPinstructionMix[count,])
	      
	      # Data reuse distributions
	      crtThread[["dataReuseDistribution"]] <- list()
	      crtDTR <- list()
	      indexDTR <- 1\n""")
		f.write('      crtDTR[["cacheLineSize"]] <- "{0}"'.format(instrumentation_values['DATA_CACHE_LINE_SIZE']))
		f.write("""
	      crtDTR[["statistics"]][["data"]] <- data[[1]]$threads$reuseDistributions[[count]]$data[[1]]
	      crtDTR[["statistics"]][["dataCDF"]] <- data[[1]]$threads$reuseDistributions[[count]]$dataCDF[[2]]
	      crtThread[["dataReuseDistribution"]][[indexDTR]] <- crtDTR
	      
	      # Instruction-level parallelism (ILP)
	      crtThread[["ilp"]] <- list()
	      crtILP <- list()
	      indexILP <- 1\n""")
		f.write('      crtILP[["windowSize"]] <- "{0}"'.format(instrumentation_values['WINDOW_SIZE']))
		f.write("""
	      crtILP[["statistics"]] <- list()
	      crtILP[["statistics"]][["span"]] <- data[[1]]$threads$ilp[count,1]
	      crtILP[["statistics"]][["arithmetic_mean"]] <- data[[1]]$threads$ilp[count,2]
	      crtThread[["ilp"]][[indexILP]] <- crtILP
	      
	      # Instruction reuse distributions
	      crtThread[["instReuseDistribution"]] <- list()
	      crtITR <- list()
	      indexITR <- 1\n""")
		f.write('      crtITR[["instructionSize"]] <- "{0}"\n'.format(instrumentation_values['INST_SIZE']))
		f.write('      crtITR[["cacheLineSize"]]   <- "{0}"'.format(instrumentation_values['INST_CACHE_LINE_SIZE']))
		f.write("""
	      crtITR[["statistics"]][["instructions"]] <- data[[1]]$threads$reuseDistributions[[count]]$instructions[[3]]
	      crtITR[["statistics"]][["instructionsCDF"]] <- data[[1]]$threads$reuseDistributions[[count]]$instructionsCDF[[4]]
	      crtThread[["instReuseDistribution"]][[indexITR]] <- crtITR
	      
	      registerAnalysis <- FALSE
	      # Register accesses
	      for(index in 1:length(names(data$swProperties$threads)))
	        if (grepl("register", names(data$swProperties$threads)[index])) { 
	          registerAnalysis <- TRUE
	          break
	        }
	      
	      # TODO: Adapt once you have an input file with register accesses
	      if (registerAnalysis) {
	        crtThread[["registerAccesses"]] <- data.frame()
	        crtREG <- list()
	        crtREG[["reads"]] <- data[[1]]$threads$registerAccesses$reads[[count]]
	        crtREG[["writes"]] <- data[[1]]$threads$registerAccesses$writes[[count]]
	        crtThread[["registerAccesses"]] <- crtREG
	      }
	      
	      JSONelements[["threads"]][[count]] <- crtThread
	      count <- count + 1
	  }
	  
	  sink(outputFile)
	  print(toJSON(JSONelements,pretty=T,auto_unbox=T))
	  sink() 
	}
	mergeToJSON()
	""")

	# lunch the Rscript
	rscript = subprocess.Popen(['Rscript', 'convert.R'], cwd=os.getcwd())
	stdout, stderr = rscript.communicate()







if __name__ == "__main__":

	arg_parser = argparse.ArgumentParser(description='grab all the profile files and store them in training and test folders')
	arg_parser.add_argument('--out', dest='out', type=str, default=os.getcwd(), help='the output path for the generated directory' )
	arg_parser.add_argument('--application', dest='app', type=str, help='The application name')
	arg_parser.add_argument('--benchmark', dest='bench', type=str, help='The benchmark name')
	arg_parser.add_argument('source', type=str, nargs='?', default=os.getcwd(), help='the root path where the profile files are stored')
	args = arg_parser.parse_args()

	# grab all the profile files
	data_files = get_pisa_profiles(args.source)

	# copy the files
	path = os.path.join(args.out, 'profiles')
	mkdir_p(path)
	for f in data_files:
		root, extension = os.path.splitext(os.path.basename(f))
		out_file = '{0}.profile'.format(root)
		convert_and_copy(f, os.path.abspath(os.path.join(args.out, 'profiles', out_file)), args.app, args.bench)
