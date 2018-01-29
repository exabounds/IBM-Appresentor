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
		data_files.extend([os.path.join(dirpath, x) for x in filenames if x.endswith('.profile')])

	# safe check
	if not data_files:
		#print('PLOT: Unable to find any profile files, aborting...')
		sys.exit(os.EX_NOINPUT)

	return data_files


if __name__ == "__main__":

	arg_parser = argparse.ArgumentParser(description='grab all the profile files and store them in training and test folders')
	arg_parser.add_argument('--out', dest='out', type=str, default=os.getcwd(), help='the output path for the generated directory' )
	arg_parser.add_argument('source', type=str, nargs='?', default=os.getcwd(), help='the root path where the profile files are stored')
	args = arg_parser.parse_args()

	# grab all the profile files
	data_files = get_pisa_profiles(args.source)

	# copy the files
	path = os.path.join(args.out, 'profiles')
	mkdir_p(path)
	for f in data_files:
		shutil.copy(f, os.path.join(path, os.path.basename(f)))
