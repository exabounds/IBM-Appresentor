########## 2mm configuration file ##########

# define here the parameter of the application
def getInputParameterRange(dsName):
	"""
	This function defines the input parameter for the
	given application.
	Parameters:
		None
	Return:
		A dictionary with the input ranges:
			- key    -> string, the name of the parameter wrt the Makefile
			- values -> a list of string that represents the allowed input values
	"""

	found = False;
	
		
	if(dsName == "testOMP"):
		found = True
		print('[INFO] DOE \"testOMP\" found!')
		build_input = {
		}

		run_input = {
		'-s' 	: [ '9' , '10' , '11' , '12' , '13' ]
		}

		omp_threads = ['4', '5', '6','7','8'] # an empty dictionary means no OpenMP

		mpi_procs = ['64', '64', '125' , '216', '216' ] # an empty dictionary means no MPI
		
		
	if(dsName == "trainOMP"):
		found = True
		print('[INFO] DOE \"trainOMP\" found!')
		build_input = {
		}

		run_input = {
		'-s' 	: [ '4' , '5' , '7' , '9' , '10' ]
		}

		omp_threads = ['2', '3', '4', '5', '6'] # an empty dictionary means no OpenMP

		mpi_procs = ['27' , '27', '64', '125' , '125' ] # an empty dictionary means no MPI
		
		
	if(dsName == "test"):
		found = True
		print('[INFO] DOE \"test\" found!')
		build_input = {
		}

		run_input = {
		'-s' 	: [ '9' , '10' , '11' , '12' , '13' ]
		}

		omp_threads = ['1'] # an empty dictionary means no OpenMP

		mpi_procs = ['64', '125', '216' , '343', '343' ] # an empty dictionary means no MPI
		
		
		
	###################### default, "train
	if(not found):# default, "train"
		print('[INFO] using DOE \"train\"!')
		build_input = {
		}

		run_input = {
		'-s' 	: [ '4' , '5' , '7' , '9' , '10' ]
		}

		omp_threads = ['1'] # an empty dictionary means no OpenMP

		mpi_procs = ['27' , '64', '125', '216' , '216' ] # an empty dictionary means no MPI
		
	return build_input, run_input, omp_threads, mpi_procs

	
# define the dimension of the used data structures
def getDimensionNumber():
	return 0
