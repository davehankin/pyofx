"""
pyofx - OrcFxAPI wrapper

"""
import time
import os
import tempfile
import ctypes
import csv
from subprocess import Popen, PIPE, STDOUT
import StringIO

from OrcFxAPI import *
_is64bit = ct.sizeof(ct.c_voidp) == 8
if os.name != 'nt':
	raise OFXError("Are you mad? Nothing here will work unless you are on Windows!")

class OFXError(Exception):
	'''Branded errors so we know it's our fault'''
	pass

def check_licence():
	''' Returns True if a licence can be found. Useful for polling to wait for a free licence.
	See examples.py''' 
	try:
		_m=Model()
		return True
	except DLLError:
		return False

def get_modes(model, line, from_mode=-1, to_mode=100):
	''' Returns a tuple with (Mode Number, Modal Period, Modal Frequency) for modal analysis of
	lines. Check specifc range of modes with from_mode and to_node.'''
	model.CalculateStatics()
	modes = Modes(line, ModalAnalysisSpecification(True, from_mode, to_mode))
	return ((mode+1,modes.modeDetails(mode).period,
			 1/modes.modeDetails(mode).period) for mode in range(modes.modeCount))

def get_unc_path(local_name):
	''' return the UNC path of a mapped drive. Useful becuase some distributed OrcaFlex versions 
	want only networked filepaths. Returns None if the drive is not mapped (e.g. C:\)'''
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
		
		
class Model(Model):
	''' Wrapper around OrcFxAPI.Model to add extra functionality. 
	
	1. added path attribute so the location of the model on the disc can be found from:
	
	>>> import pyofx
	>>> model = pyofx.Model(r"C:\path\to\data_file.dat")
	>>> model.path
	"C:\path\to\data_file.dat"
	
	2. added the open method. This will open the model in the OrcaFlex GUI, if the model
	does not exist on disc then a windows temp file will be created. 
	'''
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
		
			
	def open(self):
		if not self.path:
			fd, self.path = tempfile.mkstemp(suffix=".dat")
			os.close(fd)
			self.SaveData(self.path) 
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
		
	def SaveSimulation(self, filename):
		Model.SaveSimulation(self, filename)
		self.path=filename
	
	
		
class Models(object):
	
	def __init__(self, directories, filetype="dat",
				 subdirectories=False, return_model=True, 
				 filter_function=None,failed_function=None):
		'''
		Generator for Model objects. Requires a directory as a string or a list of directories as 
		strings. Other arguments are:
		
		filetype 	     str    "dat" or "sim" to return data files or simulations (default="dat")
		subdirectories   bool   if True then subdirectories will be included (default=False)
		return_model     bool   if True then yeilds pyofx.Model objects, if False yeilds a string
								represetneing the full path to the file. (default=True)
		filter_function  func   function that returns True or False when passed the full filename
		failed_function  func   function to be performed on failed simulation file loads [TODO]
		'''
		self._dirs = []
		self.filetype = filetype
		self.sub = subdirectories
		self.return_model = return_model
		
		if filter_function is None:
			self.filter_function = lambda s: True
		else:
			self.filter_function = filter_function	
		
		if failed_function and  filetype=="sim":
			self.failed_function = failed_function
		
		if type(directories) == str:
			self._dirs.append(directories)
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
			model_path = os.path.join(root,filename)
			if self.return_model:
				return Model(model_path)
			else:
				return model_path
		
		for d in self._dirs:
			if self.sub:
				for r,d,f in os.walk(d):
					for file_ in f:
						if self.filter_function(os.path.join(r,file_)) and file_.endswith(extension):
							yield model_or_path(r,file_)
			else:
				for file_ in os.listdir(d):
					if self.filter_function(os.path.join(d,file_)) and file_.endswith(extension):
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
		>>> print "All jobs finished" # This won't print unitl the simulations are complete. 
		     
	"""  
	
	def __init__(self, dllname=None): 		
		
		
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
				
		if not dllname:
			try:
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
								 'Software\\Orcina\\Distributed OrcaFlex',
								  0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
					self.dllname = winreg.QueryValueEx(key,'DOFWorkingDirectory')[0]
			except WindowsError:
				try:
					with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
									 'Software\\Orcina\\DistributedOrcaFlex',
									  0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
						self.dllname = winreg.QueryValueEx(key,'DOFWorkingDirectory')[0]
				except:
					OFXError("An attempt to find the location of OrcFxAPI.dll failed.")
		else:
			self.dllname = dllname														
		
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

		