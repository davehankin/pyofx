import time
import os
from OrcFxAPI import *
from subprocess import Popen, PIPE, STDOUT
from numpy import asarray


class OFXError(Exception):
	'''Branded errors so we know it's our fault'''
	pass

def check_licence():
	try:
		_m=Model()
		return True
	except OrcFxAPI.DLLError:
		return False

def get_modes(model, line, from_mode=-1, to_mode=100):
	model.CalculateStatics()
	modes = Modes(line, ModalAnalysisSpecification(True, from_mode, to_mode))
	return [(mode+1,modes.modeDetails(mode).period, 1/modes.modeDetails(mode).period) for mode in range(modes.modeCount)]
	
class pyModel(Model):
	def __init__(self,*args,**kwargs):
		super(pyModel, self).__init__(*args,**kwargs)
		if kwargs.get('filename', False):
			self.path = kwargs.get('filename')
		elif len(args)>0:
			if os.path.exists(args[0]):
				self.path = args[0]
		else:
			self.path = None
			
	def open_gui(self):
		
		with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'Software\\Orcina\\OrcaFlex\\Installation Directory', 0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
			installationDirectory = winreg.QueryValueEx(key, 'Normal')[0]
		
		cmd_line = ['OrcaFlex.exe', self.path]
		
		try:
			assert os.path.isdir(installationDirectory)
		except AssertionError as error:
			raise OFXError("{} might not be a directory".format(installationDirectory))
		
		os.chdir(installationDirectory)
		p = Popen(cmd_line, cwd=installationDirectory, stdout=PIPE, universal_newlines=True, stderr=STDOUT, shell=False)
		p.communicate()
		
class Models(object):
	
	def __init__(self, directories, filetype="dat", sub=False, return_model=True):
		self.dirs = []
		self.filetype = filetype
		self.sub = sub
		self.return_model = return_model
		if type(directories) == str:
			self.dirs.append(directories)
		else:
			for _dir in directories:
				if type(_dir) != str:
					raise OFXError("Directory argurments need to be strings. {} is a {}.".format(_dir, type(_dir)))
				else:
					if os.path.isdir(_dir):
						self.dirs.append(_dir)
					else:
						raise OFXError("{} does not appear to be a vaild directory. hint:put an 'r' before the string e.g. r'c:\temp'.".format(_dir, type(_dir)))
		
	def __iter__(self):
		extension = "." + self.filetype
		def model_or_path(root, filename):
			if self.return_model:
				return pyModel(os.path.join(root,filename))
			else:
				return os.path.join(root,filename)
		for d in self.dirs:
			if self.sub:
				for r,d,f in os.walk(d):
					for file_ in f:
						if file_.endswith(extension):
							yield model_or_path(r,file_)
			else:
				for file_ in os.listdir(d):
					if file_.endswith(extension):
						yield model_or_path(d,file_)


class ULSResult(object): 
      
    def __init__(self, ofxobject, variable, extreme, node=None, arc_length=None, section=None): 
        """ Result - OrcaFlex extreme result required object. 
        Inputs: 
        ofxobject - Name of the object in OrcaFlex to extract results from. 
        variable - Data value to extract results for. 
        extreme - "Max" or "Min" for extrema to analyse. 
        [optional] node - Node to extract results for. 
        [optional] arc_length - Arc length to extract results for. 
        [optional] section - Line section to extract results for. 
          
        Methods: 
        Result.extreme_stats() - runs extreme stats on a Result object which has a valid time_history attribute 
          
        Output: 
          
        Result.time_history = values from ULS.extract. 
        Result.threshold_factor = factor applied to maximum value to obtain exceedence threshold. 
        Result.exeecdence_threshold = value fo exceedence threshold used. 
        Result.maximum_most_probable_level = Most probable value. 
          
        """
        self.ofxobject = ofxobject 
        self.variable = variable 
        self.extreme = extreme         
        self.node = node 
        self.section = section 
        self.arc_length = arc_length 
        self.time_history=[] 
        if len(filter(lambda a: a!=None, [node, section, arc_length])) > 1:         
            raise AttributeError("Specify one or none of node, arc_length or section.") 
          
    def extreme_stats(self): 
        if not self.time_history: 
            raise AttributeError("No time history data present for this result") 
        else:         
            error = True
            self.threshold_factor = 0.8
            while error:                 
                if self.extreme  == "Max": 
                    self.exeecdence_threshold = self.threshold_factor*max(self.time_history) 
                    Specification=LikelihoodStatisticsSpecification(evdGPD, self.exeecdence_threshold, OrcinaDefaultReal(), exUpperTail) 
                else: 
                    self.exeecdence_threshold = self.threshold_factor*min(self.time_history) 
                    Specification=LikelihoodStatisticsSpecification(evdGPD, self.exeecdence_threshold, OrcinaDefaultReal(), exLowerTail)                 
                extremeStats = ExtremeStatistics(asarray(self.time_history), self.log_interval)     
                extremeStats.Fit(Specification)             
                query=LikelihoodStatisticsQuery(3.0,95.0) 
                maximum_most_probable = extremeStats.Query(query)         
                self.maximum_most_probable_level=maximum_most_probable.ReturnLevel                 
                if (self.extreme == "Max") and (self.maximum_most_probable_level>0.0):                     
                    error = False                    
                elif self.extreme == "Min" and (self.maximum_most_probable_level<0.0):                     
                    error = False                            
                else: 
                    self.threshold_factor -=0.1
                    print "attempting a threshold of %f of max values" % self.threshold_factor                     
        return self
          
    def __str__(self): 
          
        header = """\n<--- %s %s for %s --->\n""" % (self.variable, self.extreme, self.ofxobject)          
        region = filter(lambda a: a[0]!=None, zip([self.node, self.section, self.arc_length],['Node', 'Section', 'Arc Length(m)']))         
        if region: 
            text_region = """[%s = %s]""" % (region[0][1], str(region[0][0])) 
        else: 
            text_region = "" 
        final_values = """\nwith a %1.1f threshold factor applied to yield %f exceedance threshold,\nthe most probable 3hr return value is:\n\n%f\n""" % (self.threshold_factor,self.exeecdence_threshold, self.maximum_most_probable_level)         
        return header+text_region+final_values 
  
  
def process_uls_folder(direcetory, data_to_extract): 
        """ 
        data_to_extract should be a list of ULSResult objects 
        e.g. data_to_extract = [ULSResult('Line1','Curvature', 'Max')] 
        ULS(base_case).extract(data_to_extract) 
        """
        models = Models(direcetory, filetype='sim')
        g = models[0]['General'] 
        log_interval = g.ActualLogSampleInterval 
          
        def time_histories(obj, result): 
              
            def end_or_mid(node, range):                 
                if node == 0:                     
                    obj_extra = oeEndA                     
                elif node == len(range):                     
                    obj_extra = oeEndB                     
                else:                     
                    obj_extra = oeNodeNum(node)                     
                return obj_extra 
              
            if result.node:                 
                time_history = obj.TimeHistory(result.variable,Period(1), oeNodeNum(result.node))                 
            elif result.arc_length:                 
                time_history = obj.TimeHistory(result.variable,Period(1), oeArcLength(result.arc_length))                 
            elif result.section:                             
                if result.extreme == 'Max': 
                    range = obj.RangeGraph(result.variable,Period(1), arclengthRange=arSpecifiedSections(result.section,result.section)) 
                    max_range = range.Max
                    arc_range = range.X 
                    max_var = max_range.max() 
                    max_var_node = max_range.argmax()   
                    time_history = obj.TimeHistory(result.variable,Period(1), oeArcLength(arc_range[max_var_node])) 
                      
                elif result.extreme  == 'Min': 
                    range = obj.RangeGraph(result.variable,Period(1), arclengthRange=arSpecifiedSections(result.section,result.section)) 
                    min_range = range.Min
                    arc_range = range.X 
                    min_var = min_range.min() 
                    min_var_node = min_range.argmin()   
                    time_history = obj.TimeHistory(result.variable,Period(1), oeArcLength(arc_range[min_var_node]))                 
                else: 
                    raise IOError("Needs to be 'Max' or 'Min'.")             
            else: 
              
                if result.extreme  == 'Max': 
                    max_range =  obj.RangeGraph(result.variable,Period(1)).Min
                    max_var = max_range.max() 
                    max_var_node = max_range.argmax()                                  
                    obj_extra = end_or_mid(max_var_node, max_range)                     
                    time_history = obj.TimeHistory(result.variable,Period(1), obj_extra)                     
                elif result.extreme  == 'Min': 
                    min_range =  obj.RangeGraph(result.variable,Period(1)).Min
                    min_var = min_range.min() 
                    min_var_node = min_range.argmin()                                  
                    obj_extra = end_or_mid(min_var_node, min_range)                     
                    time_history = obj.TimeHistory(result.variable,Period(1), obj_extra)          
            return time_history 
  
        for m in models:
            if m.simulationComplete: 
                for result in data_to_extract: 
                      
                    obj = m[result.ofxobject]   
                    result.time_history += list(time_histories(obj,result)) 
                    result.log_interval = log_interval
       		else:
       			print "NOT COMPLETE:\n{}\n{}".format(m.path, m.status)
          
        results = [result.extreme_stats() for result in data_to_extract] 
        return results 

	

if __name__ == "__main__":
	for m in Models(r"Y:\Design\Technology\Dynamic Analysis\1) JR Specific\JR100523 FMC\04) Models", return_model=False):
		print m

		