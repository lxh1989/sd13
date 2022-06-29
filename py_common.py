#! /usr/bin/env/python 3.0
#
# Contains common functions necessary for various python testcase scripts.
#

import os, re, csv, datetime, subprocess, glob, sys, time, shutil

def is_generated_file(fullfilepath):
	"""
	Determines if the first line of a file contains the autogenerated signature string.
	"""
	with open(fullfilepath, 'r') as f:
		firstline = f.readline()
		if firstline.strip() == get_engine_signature():
			return True
	return False

def find_files_in_dir(directory, regex, silent=True):
	"""
	Finds files (non-directories) that match a regex in a certain directory.  (recursively, case-insensitive)
	Can pass an optional argument of silent=False to print filenames that did not match the regex.
	"""
	matching_files = []
	for root, dirs, files in os.walk(directory):
		for name in files:
			result = re.search(regex, name, re.IGNORECASE)
			if result != None:
				matching_files.append(os.path.realpath(os.path.join(root, name)))
			else:
				if not silent:
					print("Skipped file (did not match regex): ", name)

	return matching_files

def find_directories_in_dir(directory, regex, silent=True):
	"""
	Finds directories that match a regex in a certain directory (recursively, case-insensitive)
	Can pass an optional argument of silent=False to print filenames that did not match the regex.
	"""
	matching_directories = []
	for root, dirs, files in os.walk(directory):
		for name in dirs:
			result = re.search(regex, name, re.IGNORECASE)
			if result != None:
				matching_directories.append(os.path.realpath(os.path.join(root, name)))
			else:
				if not silent:
					print("Skipped dir (did not match regex): ", name)

	return matching_directories

def find_all_files_in_dir_nr(directory):
	"""
	Finds all files (non-directories) in a directory.  This function is not recursive.
	"""
	files = os.listdir(directory)

	# append base dir
	files = list(map(lambda x: os.path.join(directory, x), files))

	# make sure each path is a file (and not a directory)
	files = list(filter(lambda x: os.path.isfile(x), files))

	return files

def find_testcase_functional_variants_in_dir(dir):
	"""
	Finds all functional variants in a directory. This was originally created when
	we decided to split the test cases into separate directories by functional
	variant.
	"""
	
	func_vars = []
	
	# filter the list of test cases to the baseline test cases so that we can
	# iterate over this list without worrying about duplicate functional variants
	baseline_testcases = find_files_in_dir(dir, get_baseline_functional_variant_regex())
	
	for btc in baseline_testcases:
		btc_file_name = os.path.basename(btc)
		result = re.search(get_testcase_filename_regex(), btc_file_name, re.IGNORECASE)

		if result != None:
			func_vars.append(result.group('functional_variant_name'))
		else:
			print_with_timestamp('Could not determine the functional variant in ' + btc_file_name)
			exit(1)

	return func_vars
	
def open_file_and_get_contents(file):
	"""
	Returns the entire contents of a file as one large string.
	"""
	with open(file, 'r') as f:
		try:
			content = f.read()
			return content
		except UnicodeDecodeError as error:
			print("\n\n")
			print(error)
			print("Weird char in ", file)
			print("\n")
			return None;

def open_file_and_get_lines(file):
	"""
	Returns the file as a list of lines
	"""
	with open(file, 'r') as f:
		try:
			lines = f.readlines()
			return lines
		except UnicodeDecodeError as error:
			print("\n\n")
			print(error)
			print("Weird char in ", file)
			print("\n")
			return None;

def write_file(filename, contents):
	"""
	Write contents to file.
	"""
	with open(filename, 'w') as f:
		f.write(contents)

def read_csv(filename):
	"""
	Reads a csv.
	"""
	raw_records = []
	with open(filename, 'r') as f:
		reader = csv.reader(f, dialect='excel')
		for row in reader:
			raw_records.append(row)
	
	return raw_records

def read_csv_with_header(filename):
	"""
	Reads a csv and returns the header along with the records.
	"""
	raw_records = read_csv(filename)

	header = raw_records.pop(0)

	return header, raw_records

def write_csv(filename, records):
	"""
	Writes a list to a csv.
	"""
	with open(filename, 'w', newline='') as f:
		writer = csv.writer(f, dialect='excel')
		for r in records:
			writer.writerow(r)

def transform_csv(input_file, output_file, header_fx=None, row_fx=None):
	"""
	Transforms a csv using streaming technique.  Calls a header function that
	allows the caller to modify the header; also calls a row function that
	allows the caller to modify each row in csv.

	Allows the caller to pass arbitrary arguments between the header fx
	and row fx.

	The header function should look like (at a minimum):
		def header_fx(header):
			data = "data to share with row_fx"
			return header, data

	The row function declaration should look like (at a minimum):
		def row_fx(orig_header, new_header, row, data):
			return row

	"""

	with open(input_file, 'r', newline='') as fi:
		reader = csv.reader(fi, dialect='excel')
		orig_header = next(reader)

		if header_fx == None:
			new_header, data = orig_header, None
		else:
			new_header, data = header_fx(orig_header)

		with open(output_file, 'w', newline='') as fo:
			writer = csv.writer(fo, dialect='excel')
			writer.writerow(new_header)

			for row in reader:

				if row_fx == None:
					pass
				else:
					row = row_fx(orig_header, new_header, row, data)

				writer.writerow(row)
	
	return output_file

def get_c_good_fx_counting_regex():
	"""
	This is not used to figure out ALL C good functions.  This regex is a way of counting
	how many non-flawed constructs we have per testcase.
	"""
	return "good(\d+|G2B|B2G|G2B\d+|B2G\d+)"

def get_java_good_fx_counting_regex():
	"""
	This is not used to figure out ALL Java good functions.  This regex is a way of counting
	how many non-flawed constructs we have per testcase.
	"""
	return "good(\d+|G2B|B2G|G2B\d+|B2G\d+)"

def get_testcase_filename_regex():
	"""
	This regex matches primary and secondary test case files.
	Matches must be performed case-insensitive. (re.IGNORECASE)

	If you change this regex, update the C# common library regex.
	If you change this regex, update the primary testcase filename regex.
	"""

	return "^cwe" + \
		"(?P<cwe_number>\d+)" + \
		"_" + \
		"(?P<cwe_name>.*)" + \
		"__" + \
		"(?P<functional_variant_name>.*)" + \
		"_" + \
		"(?P<flow_variant_id>\d+)" + \
		"_?" + \
		"(?P<subfile_id>[a-z]{1}|(bad)|(good(\d)+)|(base)|(goodB2G)|(goodG2B))?" + \
		"\." + \
		"(?P<extension>c|cpp|java|h)$"

def get_primary_testcase_filename_regex():
	"""
	This regex matches only primary test case files.
	Matches must be performed case-insensitive. (re.IGNORECASE)

	The "(?!8[12]_bad)" is a "negative lookahead" so that we don't 
	get the 81_bad or 82_bad file as the primary since those flow 
	variants also have an "a" file (which is the primary file)
	
	The "(?!CWE580.*01_bad.java)" prevents getting the _bad file for 
	CWE580 since it also has an "a" file.
	"""

	return "^(?!CWE580.*01_bad.java)" + \
		"cwe" + \
		"(?P<cwe_number>\d+)" + \
		"_" + \
		"(?P<cwe_name>.*)" + \
		"__" + \
		"(?P<functional_variant_name>.*)" + \
		"_" + \
		"(?!8[12]_bad)" + \
		"(?P<flow_variant_id>\d+)" + \
		"_?" + \
		"(?P<subfile_id>a|(_bad))?" + \
		"\." + \
		"(?P<extension>c|cpp|java)$"
		
def get_baseline_functional_variant_regex():
	"""
	This regex matches only baseline test case files
	and can be used to calculate the number of functional variants.
	Matches must be performed case-insensitive. (re.IGNORECASE)

	The "(?!CWE580.*01_bad.java)" prevents getting the _bad file for 
	CWE580 since it also has an "a" file.
	"""
	
	return "^(?!CWE580.*01_bad.java)CWE\d+.*_01((a)|(_?bad)|)\.(c|cpp|java)?$"

def get_functionname_c_regex():
	"""
	Used to get the "simple" function name for c functions.
	"""
	return "^(CWE|cwe)(?P<cwe_number>\d+)_(?P<cwe_name>.*)__(?P<function_variant>.*)_(?P<flow_variant>\d+)(?P<subfile_id>[a-z]*)_(?P<function_name>[^.]*)$"
	
def get_cwe_id_regex():
	"""
	Used to get the CWE ID from a test case file or path name
	"""
	return "(CWE\d+)_"
	
def get_java_testcase_lib():
	"""
	Used to get the path to the Java test case lib directory
	"""
	return "..\\..\\..\\lib"
	
def get_java_testcase_lib_split():
	"""
	Used to get the path to the Java test case lib directory from a split directory
	"""
	return "..\\" + get_java_testcase_lib()
	
def get_c_and_cpp_testcasesupport_dir():
	"""
	Used to get the path to the C/C++ test case support directory
	"""
	return "..\\..\\testcasesupport"
	
def get_c_and_cpp_testcasesupport_dir_split():
	"""
	Used to get the path to the C/C++ test case support directory from a split directory
	"""
	return "..\\" + get_c_and_cpp_testcasesupport_dir()
	
def get_testcase_subdirectory_regex():
	"""
	Used to get the regex that will match the split test case CWE ID
	Starting in 2012 the CWE ID will be of the form: CWEXYZ_s01, CWEXYZ_s02, etc.
	"""
	return "CWE.*_s\d{2,}$"

def get_timestamp():
	"""
	Returns a timestamp of the form YYYY-MM-DD.
	"""
	date = datetime.date.today()
	return str(date)
	
def get_engine_signature():
	"""
	This is the first line in a test case that has been auto-generated
	by the Test Case Engine. We use this to identify auto-generated vs.
	manually-genenerated test cases.
	"""
	return "/* TEMPLATE GENERATED TESTCASE FILE"
	
def get_java_main_comment():
	"""
	This is the comment that appears on the line directly above the main() method in the
	Java test cases.
	"""
	return "Below is the main()"
	
def get_c_cpp_main_comment():
	"""
	This is the comment that appears on the line directly above the main() function in the
	C/C++ test cases.
	"""
	return "Below is the main()"
	
def get_tool_study_max_java_heap_size():
	"""
	Some of the tools allow you to specify the java heap size. We want to ensure all of the tools
	use the same heap size (if they allow it to be specified), so the run_analysis scripts
	should use this method to retrieve the size
	"""
	return "4096m"

def map_weakness_classes(file):
	"""
	Reads the weakness class csv file.  Allows a cwe to be part of multiple weakness classes.
	"""
	header, records = read_csv_with_header(file)

	dict = {}

	for record in records:
		cwe = record[header.index("CWEID")]
		wclass = record[header.index("Weakness Class")]
		if cwe in dict.keys():
			dict[cwe].append(wclass)
			# may want to error here instead
			print_with_timestamp("WARNING: CWE \"" + cwe + "\" is assigned to more than 1 weakness class.")
		else:
			dict[cwe] = [wclass]

	return dict

def print_with_timestamp(contents):
	"""
	Print a string with the timestamp at the beginning of the line.
	"""
	print("[" + time.ctime(None) + "] " + contents)
	
def run_commands(commands, use_shell=False):
	"""
	Runs a command as if it were run in the command prompt.  If you need to use commands such as
	"cd, dir, etc", set use_shell to True.
	"""
	command = " && ".join(commands)
	
	# Not using print_with_timestamp() here since we want to capture the time for the time diff
	time_started = time.time()
	print("[" + time.ctime(time_started) + "] Started command: \"" + command + "\"")
	sys.stdout.flush()
	
	subprocess.check_call(command, shell=use_shell, stderr=sys.stderr, stdout=sys.stdout)
	
	# Not using print_with_timestamp() here since we want to capture the time for the time diff
	time_ended = time.time()
	print("[" + time.ctime(time_ended) + "] Finished command: \"" + command + "\"")
	
	elapsed_seconds = time_ended-time_started
	print_with_timestamp("Command \"" + command + "\" took " + str(elapsed_seconds) + " seconds to complete.")

def run_analysis(test_case_path, build_file_regex, run_analysis_fx):
	"""
	Helper method to run an analysis using a tool.  
	Takes a test case path, build file regex and a function pointer.
	"""

	time_started = time.time()

	# find all the files
	files = find_files_in_dir(test_case_path, build_file_regex)
	
	# run all the files using the function pointer
	for file in files:

		# change into directory with the file
		dir = os.path.dirname(file)
		os.chdir(dir)

		# run the the file
		file = os.path.basename(file)
		run_analysis_fx(file)

		# return to original working directory
		os.chdir(sys.path[0])
	
	time_ended = time.time()

	print_with_timestamp("Started: " + time.ctime(time_started))
	print_with_timestamp("Ended: " + time.ctime(time_ended))

	elapsed_seconds = time_ended-time_started
	print_with_timestamp("Elapsed time: " + convertSecondsToDHMS(elapsed_seconds))

def break_up_filename(file_name):
	"""
	Looks for various parts of the filename to place into the new columns.
	"""

	cwe_num = ''
	cwe_name = ''
	fx_var = ''
	flow_var = ''
	subfile = ''
	lang = ''

	result = re.search(get_testcase_filename_regex(), file_name, re.IGNORECASE)

	if result == None:

		# use blank values
		print_with_timestamp("WARNING: file \"" + file_name + "\" is not going to be parsed into parts! (blank values will be used)")
	else:
		# its a normal testcase file
		cwe_num = result.group('cwe_number')
		cwe_name = result.group('cwe_name')
		fx_var = result.group('functional_variant_name')
		flow_var = result.group('flow_variant_id')
		subfile = result.group('subfile_id')
		lang = result.group('extension')

	parts = {}
	parts["testcase_cwe_number"] = cwe_num
	parts["testcase_cwe_name"] = cwe_name
	parts["testcase_function_variant"] = fx_var
	parts["testcase_flow_variant"] = flow_var
	parts["testcase_subfile_id"] = subfile
	parts["testcase_language"] = lang

	return parts

def break_up_cpp_function_name(function_name):
	"""
	Looks for various parts of the function name to place into the simplified function name
	"""

	result = re.search(get_functionname_c_regex(), function_name, re.IGNORECASE)

	if result == None:
		# Just use the original
		return function_name
	else:
		# Use the "simplified" portion
		return result.group("function_name")

def concatenate_csvs(input_directory, output_file):
	"""
	Combines multiple CSV files into a single CSV file.
	"""
	
	with open(output_file, 'w', newline='') as f:
		writer = csv.writer(f, dialect='excel')
		need_header = True
		
		for file in find_files_in_dir(input_directory, ".*?\.csv$"):
			header, records = read_csv_with_header(file)
			if need_header:
				writer.writerow(header)
				need_header = False
			for record in records:
				writer.writerow(record)

def generate_unique_finding_ids(input_csv, output_csv):
	"""
	Modifies CSV so that each number in the finding_id column is unique
	"""
	
	with open(input_csv, 'r', newline='') as fi:
		reader = csv.reader(fi, dialect='excel')
		header = next(reader)
		
		if 'finding_id' in header:
			finding_id_index = header.index('finding_id')
		else:
			print_with_timestamp('finding_id does not exist in CSV header')
			exit()

		with open(output_csv, 'w', newline='') as fo:
			writer = csv.writer(fo, dialect='excel')
			writer.writerow(header)

			unique_id = 1
			for row in reader:

				row[finding_id_index] = unique_id
				writer.writerow(row)
				unique_id = unique_id + 1

unique_id_count = 1
def add_unique_finding_ids(orig_header, new_header, row, data):
	"""
	Modifies CSV row so that each number in the finding_id column is unique
	Call this from transform_csv
	
	For example: transform_csv(input_file, output_file, header_fx=None, row_fx=add_unique_finding_id)
	"""
	global unique_id_count
	finding_id_index = orig_header.index('finding_id')
	row[finding_id_index] = unique_id_count
	
	unique_id_count += 1
	
	return row
	
def encode_language(input_lang):
	"""
	Checks the input language to ensure invalid file name/path characters do
	not exist in the language as it is often used to generate output file names
	in our scripts.
	
	We currently only analyze C, C++, Java, C#, and .NET code, so if a new
	language other than those listed is added we may need to review this helper
	function.
	"""
	
	encoded_lang = input_lang.replace("+", "p") # for C++
	encoded_lang = encoded_lang.replace("/", "_") # for C/C++
	encoded_lang = encoded_lang.replace("\\", "_") # for C\C++
	encoded_lang = encoded_lang.replace("#", "sharp") # for C#
	
	return encoded_lang

def move_testcase_to_split_directories(dir, functional_variants, testcase_files, file_count_limit):
	"""
	Given a directory, list of functional variants, list of testcase files, and file count limit,
	this method creates subdirectories inside the provided directory. It adds all of the files for
	a functional variant until the file_count_limit is reached. If this limit is reached, it begins
	placing the files in another subdirectory. 
	
	NOTE: All files for a given functional variant will remain in the same directory.	
	"""
	subdir_count = 1
	number_of_files_in_subdir = 0
	is_subdir_needed = True
	func_var_dir = ""
	
	for func_var in functional_variants:
		# filter the list of test cases for this functional variant
		func_var_regex = "__" + func_var + "_\d\d"
		filter_regex = re.compile(func_var_regex, re.IGNORECASE)
		func_var_testcase_files = [f for f in testcase_files if filter_regex.search(f)]
		func_var_testcase_files_count = len(func_var_testcase_files)

		if ((func_var_testcase_files_count + number_of_files_in_subdir) > file_count_limit):
			is_subdir_needed = True
	
		if is_subdir_needed == True:
			if subdir_count < 10:
				func_var_dir = os.path.join(dir, 's' + '0' + str(subdir_count))
			else: 
				func_var_dir = os.path.join(dir, 's' + str(subdir_count))
			os.mkdir(func_var_dir)
			subdir_count = subdir_count + 1
			is_subdir_needed = False
			number_of_files_in_subdir = func_var_testcase_files_count
		else:
			number_of_files_in_subdir = number_of_files_in_subdir + func_var_testcase_files_count
		
		# Copy the files for this functional variant to the new directory
		# and remove the file from the CWE root directory
		print_with_timestamp("Moving the test cases for the following functional variant \"" + func_var + "\" to subdirecory \"" + func_var_dir + "\"")
		for testcase_file in func_var_testcase_files:
			shutil.copy(testcase_file, func_var_dir)
			os.unlink(testcase_file)
			
def create_or_clean_directory(dir):
	"""
	This method attempts to create the specified directory. However, if it
	already exists then it will be cleaned to ensure there are no stale files.
	"""
	if not os.path.exists(dir):
		print_with_timestamp("The path \"" + dir + "\" does not exist")
		print_with_timestamp("creating directory \"" + dir + "\"")
		os.makedirs(dir)
	else: #Directory exists, but we want to clean it before use
		print_with_timestamp(dir + " already exists. Cleaning before use...")
		shutil.rmtree(dir)
		os.makedirs(dir)
		
def extract_cwe_id_from_path(path):
	"""
	This method extracts the CWE ID (and possibly sub-ID) from the path.
	It assumes that the CWE ID is contained in the path and will error
	if it not within the path.
	
	This is used most for the Java test cases when creating a project
	name in our run_analysis scripts. It's easy to get the C/C++ CWE ID
	since it is the beginning part of the batch filename. However, the Java
	scripts run on all build.xml files and therefore we need to parse the 
	CWE ID from the path containing the build.xml file.
	"""
	cwe_id = ""
	if os.path.basename(path).startswith('CWE'):
		cwe_id = re.search(get_cwe_id_regex(), os.path.basename(path)).group(1)
	# if the basename does not start with 'CWE' then we are in a sub-directory
	# and the sub-directory name is "s" plus a number (s01, s02, etc.) so we append this string
	# to the end of the CWE id to make it a unique value
	else:
		cwe_id = re.search(get_cwe_id_regex(), path).group(1)
		sub_dir = os.path.basename(path)
		cwe_id = cwe_id + '_' + sub_dir
		
	return cwe_id
	
def convertSecondsToDHMS(seconds):
	"""
	Converts seconds into days, hours, minutes, seconds
	"""
	
	if seconds >= 0 and seconds < 1:
		seconds = round(seconds, 2)
		return str(seconds)
		
	else:
		seconds  = int(round(seconds))
		
		minutes, seconds = divmod(seconds, 60)
		hours, minutes = divmod(minutes, 60)
		days, hours = divmod(hours, 24)
		
		formatStr = "{0} day{1}, {2} hour{3}, {4} minute{5}, {6} second{7}"
		output = formatStr.format( \
			  days,    "" if days==1 else "s", \
			  hours,   "" if hours==1 else "s", \
			  minutes, "" if minutes==1 else "s", \
			  seconds, "" if seconds==1 else "s")
			  
		return output
		
