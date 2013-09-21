import time
import os
import tempfile
import ctypes
import csv
from subprocess import Popen, PIPE, STDOUT
import StringIO
from progress_meter import withprogress
from OrcFxAPI import *

class OFXError(Exception):
	'''Branded errors so we know it's our fault'''
	pass

def check_licence():
	''' Returns True if a licence can be found. Usefull for polling to wait for a free licence.
	See examples.py'''
	try:
		_m=Model()
		return True
	except OrcFxAPI.DLLError:
		return False

def get_modes(model, line, from_mode=-1, to_mode=100):
	''' Returns a tuple with (Mode Number, Modal Period, Modal Frequency) for modal analysis of
	line. Check specifc range of models with from_mode and to_node.'''
	model.CalculateStatics()
	modes = Modes(line, ModalAnalysisSpecification(True, from_mode, to_mode))
	return ((mode+1,modes.modeDetails(mode).period,
			 1/modes.modeDetails(mode).period) for mode in range(modes.modeCount))

def get_unc_path(local_name):
	''' return the UNC path of a mapped drive. Useful becuase some distributed OrcaFlex wants
	networked files. Returns None if the drive is not mapped (e.g. C:/)'''
	WNetGetConnection = ctypes.windll.mpr.WNetGetConnectionA
	ERROR_MORE_DATA = 234
	mapped_name = local_name.upper()+":"
	length = ctypes.c_long(0)
	remote_name = ctypes.create_string_buffer ("")
	result = WNetGetConnection (mapped_name,remote_name,ctypes.byref (length))
	if result == ERROR_MORE_DATA:
		remote_name = ctypes.create_string_buffer (length.value)
		result = WNetGetConnection (mapped_name,remote_name,ctypes.byref (length))
		if result != 0:
			return None
		else:
			return remote_name.value
		
@withprogress(1, color="green")
def dynamics_progress_bar(m, time, start, stop, cancel):
	
	yield (stop-time)/stop

@withprogress(1, color="green")
def progress_bar(m, time, start, stop, cancel):
	 
	yield (stop-time)/stop

@withprogress(1, color="green")
def statics_progress_bar(m, progress, cancel):
	
	yield progress
	
	

class Model(Model):
	''' Wrapper around OrcFxAPI.Model to add extra functionality.  '''
	def __init__(self,*args,**kwargs):
		super(Model, self).__init__(*args,**kwargs)
		if kwargs.get('filename', False):
			self.path = kwargs.get('filename')
		elif len(args)>0:
			if os.path.exists(args[0]):
				self.path = args[0]
			else:
				raise OFXError("\n Can't locate file {}.".format(self.path))
		else:
			self.path = None
		
		self.staticsProgressHandler = statics_progress_bar
		self.dynamicsProgressHandler = dynamics_progress_bar
			
	def Open(self):
		
		with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
						 'Software\\Orcina\\OrcaFlex\\Installation Directory',
						  0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
			installation_directory = winreg.QueryValueEx(key, 'Normal')[0]
		if _is64bit:
			cmd_line = ['OrcaFlex64.exe', self.path]
		else:
			cmd_line = ['OrcaFlex.exe', self.path]
		try:
			assert os.path.isdir(installation_directory)
		except AssertionError as error:
			raise OFXError("{} might not be a directory".format(installation_directory))
		os.chdir(installation_directory)
		p = Popen(cmd_line, cwd=installation_directory,
				 stdout=PIPE, universal_newlines=True, stderr=STDOUT, shell=False)
		p.communicate()
	
	def SaveData(self,filename):
		super(Model, self).SaveData(filename)
		self.path=filename
		
	def LoadData(self,filename):
		super(Model, self).LoadData(filename)
		self.path=filename
	
	def LoadSimulation(self,filename):
		super(Model, self).LoadSimulation(filename)
		self.path=filename
	
	
		
class Models(object):
	
	def __init__(self, directories, filetype="dat",
				 sub=False, return_model=True, filter_function=None,failed_function=None):
		self.dirs = []
		self.filetype = filetype
		self.sub = sub
		self.return_model = return_model
		
		if filter_function is None:
			self.filter_function = lambda s: True
		else:
			self.filter_function = filter_function	
		
		if failed_function and  filetype=="sim":
			self.failed_function = failed_function
		
		if type(directories) == str:
			self.dirs.append(directories)
		else:
			for _dir in directories:
				if type(_dir) != str:
					raise OFXError("""Directory argurments need to be strings.
					 {} is a {}.""".format(_dir,type(_dir)))
				else:
					if os.path.isdir(_dir):
						self.dirs.append(_dir)
					else:
						raise OFXError("""{} does not appear to be a vaild directory.
						 hint:put an 'r' before the string e.g. r'c:\temp'.
						 """.format(_dir, type(_dir)))
		
	def __iter__(self):
		extension = "." + self.filetype
		def model_or_path(root, filename):
			if self.return_model:
				return Model(os.path.join(root,filename))
			else:
				return os.path.join(root,filename)
		for d in self.dirs:
			if self.sub:
				for r,d,f in os.walk(d):
					for file_ in f:
						if self.filter_function(os.path.join(r,file_)):
							if file_.endswith(extension):
								yield model_or_path(r,file_)
			else:
				for file_ in os.listdir(d):
					if self.filter_function(os.path.join(d,file_)):
						if file_.endswith(extension):
							yield model_or_path(d,file_)

class Jobs():
	""" Python interface to Distributed OrcaFlex
		  
		>>> from pyofx import Jobs 
		>>> j = Jobs(r"\\network\path\to\OrcFxAPI.dll") 
		  
		Methods: 
		  
		add(filepath, variables=None) 
		  
		Adds an orcaflex file to the list of jobs with optional variables object.           
		
		>>> j.add(r"\\network\folder\Hs=2.2m_model.dat", {'Hs':'2.2m'}) 
		  
		run(wait=False) 
		  
		Submits jobs to Distributed Orcaflex. If wait is True it will not 
		return unitll all jobs have completed.           
		
		>>> j.run(True) 
		>>> print "All jobs finished" # This won't print unitll the simulations are complete. 
		     
	"""  
	
	def __init__(self,
				 dllname=r"\\litapp01\FEA\Apps\Orcina\Distributed OrcaFlex\Win32\OrcFxAPI.dll"): 		
		
		self.dllname = dllname 
		self.jobs = []
		try:
			with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
							 'Software\\Orcina\\Distributed OrcaFlex\\Installation Directory',
							  0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
				self.installation_directory = winreg.QueryValueEx(key, 'Normal')[0]
		except WindowsError:
			with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
							 'Software\\Orcina\\DistributedOrcaFlex\\Installation Directory',
							  0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
				self.installation_directory = winreg.QueryValueEx(key, 'Normal')[0]
		
		self.batch_fd, self.batch_path = tempfile.mkstemp(suffix=".bat") 
		self.batch_file = open(self.batch_path, 'wb') 
		self.batch_file.write('''echo off\r\n cd "%s"\r\n''' % self.installation_directory)
		self.file_list_fd, self.file_list_path = tempfile.mkstemp(suffix=".txt") 
		self.file_list_file = open(self.file_list_path, 'wb') 
	          
	def __iter__(self): 
	      
	    for job in self.jobs:
	    	yield job
	  
	      
	def add_file(self, filepath, variables=None): 
	    """ 	      
	    Adds a filepath (must be network path or a mapped drive) to the list of jobs to run. 
	    Optionally takes a variables object to represent information about the job. 
	    """
	    if filepath[:2] != r"\\":
	    	if get_unc_path(filepath[0]):
	    		filepath = get_unc_path(filepath[0]) + filepath[2:]
	    	else:	
	        	raise OFXError("{} must be a network filepath (or mapped drive).".foramt(filepath)) 
	    try: 
	        a = open(filepath) 
	        a.close() 
	        del a             
	    except IOError: 
	        raise OFXError("{} not a vaild file.".format(filepath)) 
	    self.jobs.append((filepath,variables)) 
	    self.file_list_file.write('''{}\r\n'''.format(filepath)) 
	      
	def run(self, wait=False): 
	    """         
	    Submit the jobslist to Distributed Orcaflex. 
	    If wait=True then wait until the jobs complete to return. 
	    """
	    if wait: 
	        cmdline = 'dofcmd -add -wait -dllname="{}" "{}"\r\n'.format(self.dllname,
																	  self.file_list_path) 
	    else: 
	        cmdline = 'dofcmd -add -dllname="{}" "{}"\r\n'.format(self.dllname,
																self.file_list_path) 
	    self.batch_file.write(cmdline) 
	    os.close(self.batch_fd) 
	    os.close(self.file_list_fd) 
	    self.batch_file.close() 
	    self.file_list_file.close() 
	    batch = self.batch_path.split('\\')	    
	    p = Popen(self.batch_path, cwd='\\'.join(batch[0:-1])+'\\', shell=False) 
	    stdout, stderr = p.communicate() 
	    print "Submitted {} jobs.".format(len(self.jobs)) 
	
	  
	def __del__(self):
		""" ensure we have closed the files when the object is destroyed """
		self.batch_file.close()
		self.file_list_file.close() 
	
	def list(self): 
	    """list() 	      
	    a generator for all the jobs on the Distributed Orcaflex Server. Each job will be returned
	    as a dictionary with the following keys: Job ID, Simulation file name including full path,
	    Owner, Status, Start Time, Completed Time, Name of machine last run on,
	    IP address of machine last run on, AutoSave interval, OrcFxAPI DLL version and 
	    Status string.
	    """
	    cwd = self.installation_directory
	    cmd2 = ['dofcmd.exe', '-list'] 
	    assert os.path.isdir(cwd) 
	    os.chdir(cwd)
	    p = Popen(cmd2, cwd=cwd, stdout = PIPE,
				universal_newlines = True, stderr = STDOUT, shell = True) 
	    stdout, stderr = p.communicate()        
	    if stdout is not None: 
	        whole_list = ''.join(stdout.split('\n\n')) 
	        head = ['ID', 
	                 'File', 
	                 'Owner', 
	                 'Status', 
	                 'Start Time', 
	                 'Completed Time', 
	                 'Name of machine',                          
	                 'IP address of machine', 
	                 'AutoSave interval', 
	                 'DLL version', 
	                 'Status string']
	        jobs = whole_list.split('\n')
	        jobs.reverse()
	        header = ','.join(head)    
	        jobs_list = csv.DictReader(StringIO.StringIO(header + '\n'+ '\n'.join(jobs)))	        

	        for job in jobs_list: 
	            yield job	            
	    else: 
	        raise OFXError("\n Error communicating with the distrubuted OrcaFlex server:\n"+stderr) 	

if __name__ == "__main__":
	
	j = Jobs()
	for job in j.list():
		print job.items()

		