"""
pyofx - OrcFxAPI wrapper

"""
from Tkinter import Tk
import time
import os
import tempfile
import ctypes
import csv
from subprocess import Popen, PIPE, STDOUT, check_output, CalledProcessError
import StringIO
import inspect
import math

from OrcFxAPI import *
_is64bit = ct.sizeof(ct.c_voidp) == 8


class OFXError(Exception):

    """Branded errors so we know it's our fault"""
    pass


def gamma_dnv(h_s, t_p):
    """the peak shape parameter (gamma) according to DNV-RP-H103 2.2.6.9"""
    hs13 = math.sqrt(13 * h_s)
    hs25 = math.sqrt(25 * h_s)
    if t_p <= hs13:
        return 5.0
    elif t_p > hs25:
        return 1.0
    else:
        return math.exp(5.75 - (1.15 * (t_p / math.sqrt(h_s))))


def check_licence():
    """true if a licence can be found

    Useful for polling to wait for a free licence.
    See examples.py"""
    try:
        _m = Model()
        return True
    except DLLError:
        return False


def get_modes(model, line, from_mode=-1, to_mode=100):
    """List of (Mode Number, Modal Period, Modal Frequency) tuples for modal analysis of
    lines. Check specifc range of modes with from_mode and to_mode."""
    model.CalculateStatics()
    modes = Modes(line, ModalAnalysisSpecification(True, from_mode, to_mode))
    return [(mode + 1, modes.modeDetails(mode).period,
             1 / modes.modeDetails(mode).period) for mode in range(modes.modeCount)]


def get_unc_path(local_name):
    """the UNC path of a mapped drive. 

    Useful becuase some distributed OrcaFlex versions
    want only networked filepaths. Returns None if the drive is not mapped (e.g. C:\)
    """
    WNetGetConnection = ctypes.windll.mpr.WNetGetConnectionA
    ERROR_MORE_DATA = 234
    mapped_name = local_name.upper() + ":"
    length = ctypes.c_long(0)
    remote_name = ctypes.create_string_buffer("")
    result = WNetGetConnection(
        mapped_name, remote_name, ctypes.byref(length))
    if result == ERROR_MORE_DATA:
        remote_name = ctypes.create_string_buffer(length.value)
        result = WNetGetConnection(
            mapped_name, remote_name, ctypes.byref(length))
        if result != 0:
            return None
        else:
            return remote_name.value


def dat_sim_paths(directory, name, yml=False):
    """Tuple containing full .dat and .sim filepath for filename `name` in `directory`"""
    if yml:
        return os.path.join(directory, name + '.yml'), os.path.join(directory, name + '.sim')
    else:
        return os.path.join(directory, name + '.dat'), os.path.join(directory, name + '.sim')


def vessel_drawing(length, depth, beam, bow_scale=(0.9, 0.95), vessel_type=None):
    """scale the default OrcaFlex vessel type drawing

    Given a vessel of specifed length, depth and beam. Bow shape determined by the bow_scale
    parameter. See examples vessel_scaling.png for sketch

    if an OrcaFlexObject of typeName otVesselType is passed as the vessel_type parameter then
    the drawing will be applied.
    """
    # TODO: vessel_scaling.png

    l = length / 2.0
    d = depth / 2.0
    b = beam / 2.0
    cuboid_x = [l, l, -l, -l, l, l, l, -l, -l, l]
    y = [0, b, b, -b, -b, 0, b, b, -b, -b]
    z = [d] * 5 + [-d] * 5

    bow_scaling = [1, bow_scale[0], 1, 1, bow_scale[0],
                   bow_scale[1], bow_scale[0], 1, 1, bow_scale[0]]

    z = [s * _x for s, _x in zip(bow_scaling, cuboid_x)]

    if vessel_type is not None:
        vessel_type.VertexX = x
        vessel_type.VertexY = y
        vessel_type.VertexZ = z
    else:
        return x, y, z


def buoy_drawing(size, ofx_object=None):
    _x = [1, -1, -1, 1, 1, -1, -1, 1]
    _y = [1, 1, -1, -1, 1, 1, -1, -1]
    _z = [1, 1, 1, 1, -1, -1, -1, -1]
    _sx = [float(size) * x for x in _x]
    _sy = [float(size) * y for y in _y]
    _sz = [float(size) * z for z in _z]
    if ofx_object:
        ofx_object.VertexX = _sx
        ofx_object.VertexY = _sy
        ofx_object.VertexZ = _sz
    else:
        _xyz = zip([str(x) for x in _sx], [str(y)
                   for y in _sy], [str(z) for z in _sz])
        s = ""
        for xyz in _xyz:
            s += "\t".join(xyz) + "\n"
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(s)
        r.destroy()


class Model(Model):

    """Wrapper around OrcFxAPI.Model to add extra functionality.

    1. added path attribute so the location of the model on the disc can be found from:

    >>> import pyofx
    >>> model = pyofx.Model(r"C:\path\to\data_file.dat")
    >>> model.path
    "C:\path\to\data_file.dat"

    2. added a model_name attribute (added in v0.0.9)

    >>> import pyofx
    >>> model = pyofx.Model(r"C:\path\to\data_file.dat")
    >>> model.model_name
    "data_file"

    3. added the open method. This will open the model in the OrcaFlex GUI, if the model
    does not exist on disc then a windows temp file will be created.

    4. added objects_of_type() to return a list of objects in the model of a certain types/
    e.g. model.objects_of_type('Line')
    """

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        if kwargs.get('filename', False):
            self.path = kwargs.get('filename')
        elif len(args) > 0:
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
            raise OFXError(
                "{} might not be a directory".format(installation_directory))
        os.chdir(installation_directory)
        try:
            print "{} has been opened in the OrcaFlex GUI.".format(self.path)
            p = check_output(cmd_line, universal_newlines=True)
            print "{} has been closed.".format(self.path)
        except CalledProcessError as cpe:
            raise OFXError(
                "Error opening {} in OrcaFlex:\n{}".format(self.path, cpe.output))

    def SaveData(self, filename):
        super(Model, self).SaveData(filename)
        self.path = filename

    def LoadData(self, filename):
        super(Model, self).LoadData(filename)
        self.path = filename

    def LoadSimulation(self, filename):
        super(Model, self).LoadSimulation(filename)
        self.path = filename

    def SaveSimulation(self, filename):
        super(Model, self).SaveSimulation(filename)
        self.path = filename

    @property
    def model_name(self):
        return os.path.splitext(os.path.split(self.path)[1])[0]

    def objects_of_type(self, type_name, test=None):
        """list of all objects in model with `typeName` equal to `type_name`

        option to add a test function to further filter the list
        """
        if isinstance(test, basestring):
            return filter(
                lambda o: (o.typeName == type_name) and (test in o.Name),
                self.objects)
        elif inspect.isfunction(test):
            return filter(test, filter(lambda o: (o.typeName == type_name), self.objects))
        elif test is None:
            return filter(lambda o: (o.typeName == type_name), self.objects)
        else:
            raise OFXError(
                ("The test must be for a string in the object name or a filter function. ",
                 "Was passed an {}".format(type(test))))


class Models(object):

    def __init__(self, directories, filetype="dat",
                 subdirectories=False, return_model=True,
                 filter_function=None, failed_function=None,
                 virtual_logging=False):
        """
        Generator for Model objects. Requires a directory as a string or a list of directories as
        strings. Other arguments are:

        filetype         str    "dat" or "sim" to yield data files or simulations (default="dat")
        subdirectories   bool   if True then subdirectories will be included (default=False)
        return_model     bool   if True then yield pyofx.Model objects, if False yield a string
                                of the full path to the file. (default=True)
        virtual_logging  bool   if True all returned Model instances will have virtual logging
                                enabled. Makes post processing of large sim files mmmuch quicker.
                                (default=False)
        filter_function  func   function that returns True or False when passed the full filename.
                                only models that pass the test will be returned.
        failed_function  func   function to be performed on failed simulation file loads [TODO]
        """
        self._dirs = []
        self.filetype = filetype
        if self.filetype not in ['sim', 'dat']:
            raise OFXError(
                "filetype must be 'sim' or 'dat'. [Got {}]".format(self.filetype))
        self.sub = subdirectories
        self.return_model = return_model
        self.virtual_logging = virtual_logging
        if filter_function is None:
            self.filter_function = lambda _: True
        else:
            self.filter_function = filter_function

        if failed_function and filetype == "sim":
            self.failed_function = failed_function

        if isinstance(directories,basestring):
            self._dirs.append(directories)
        else:
            for _dir in directories:
                if not isinstance(_dir,basestring):
                    raise OFXError("""Directory argurments need to be strings.
                     {} is a {}.""".format(_dir, type(_dir)))
                else:
                    if os.path.isdir(_dir):
                        self._dirs.append(_dir)
                    else:
                        raise OFXError(r"""{} does not appear to be a vaild directory.
                         hint:put an 'r' before the string e.g. r'c:\temp'.
                         """.format(_dir, type(_dir)))

    def __iter__(self):
        extension = ".{}".format(self.filetype)

        def model_or_path(root, filename):
            model_path = os.path.join(root, filename)
            if self.return_model:
                if self.virtual_logging:
                    _model = Model()
                    _model.UseVirtualLogging()
                    if self.filetype == "sim":
                        _model.LoadSimulation(model_path)
                    else:
                        _model.LoadData(model_path)
                    return _model
                else:
                    return Model(model_path)
            else:
                return model_path
        test_fun = lambda _f: self.filter_function(
            os.path.join(d, _f)) and _f.endswith(extension)
        for d in self._dirs:
            if self.sub:
                for file_ in filter(test_fun, [f for r, d, f in os.walk(d)]):
                    yield model_or_path(r, file_)
            else:
                for file_ in filter(test_fun, os.listdir(d)):
                    yield model_or_path(d, file_)


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

    def __init__(self, dllname=None):

        self.jobs = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                'Software\\Orcina\\Distributed OrcaFlex\\Installation Directory',
                                0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                self.installation_directory = winreg.QueryValueEx(
                    key, 'Normal')[0]
        except WindowsError:
            raise OFXError("Distributed OrcaFlex not found.")
        if not dllname:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    'Software\\Orcina\\Distributed OrcaFlex',
                                    0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                    self.dllname = winreg.QueryValueEx(
                        key, 'DOFWorkingDirectory')[0]
            except WindowsError:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                        'Software\\Orcina',
                                        0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
                        self.dllname = winreg.QueryValueEx(
                            key, 'DOFDefaultDLLFileName')[0]
                except:
                    raise OFXError("An attempt to find the location of OrcFxAPI.dll failed."
                                   " You should set the registry keys as advised in the "
                                   " distributed OrcaFlex manual or pass the location of the dll"
                                   " as a parameter to the Jobs object.")
        else:
            self.dllname = dllname

        self.batch_fd, self.batch_path = tempfile.mkstemp(suffix=".bat")
        self.batch_file = open(self.batch_path, 'wb')
        self.batch_file.write(
            """echo off\r\ncd "%s"\r\n""" % self.installation_directory)
        self.file_list_fd, self.file_list_path = tempfile.mkstemp(
            suffix=".txt")
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
                raise OFXError(
                    "{} must be a network filepath (or mapped drive).".format(filepath))
        try:
            a = open(filepath)
            a.close()
            del a
        except IOError:
            raise OFXError("{} not a vaild file.".format(filepath))
        self.jobs.append((filepath, variables))
        self.file_list_file.write("""{}\r\n""".format(filepath))

    def run(self, wait=False, statics=False):
        """
        Submit the jobslist to Distributed Orcaflex.
        If wait=True then wait until the jobs complete to return.
        To run statics only use statics=True
        """

        cmdline_template = '"{}" -add {}{}-dllname="{}" "{}"\r\n'
        cmdline = cmdline_template.format(
            os.path.join(self.installation_directory,
                         "dofcmd.exe"),
            "-wait " if wait else "",
            "-statics " if statics else "",
            self.dllname, self.file_list_path)

        self.batch_file.write(cmdline)
        os.close(self.batch_fd)
        os.close(self.file_list_fd)
        self.batch_file.close()
        self.file_list_file.close()
        batch = self.batch_path.split('\\')
        try:
            p = check_output(self.batch_path)
            print "Submitted {} jobs.".format(len(self.jobs))
        except CalledProcessError as cpe:
            raise OFXError(
                "Error sumbitting to Distributed OrcaFlex:\n" + cpe.output)

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
        p = Popen(cmd2, cwd=cwd, stdout=PIPE,
                  universal_newlines=True, stderr=STDOUT, shell=True)
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
            jobs_list = csv.DictReader(
                StringIO.StringIO(header + '\n' + '\n'.join(jobs)))

            for job in jobs_list:
                yield job
        else:
            raise OFXError(
                "\n Error communicating with the distrubuted OrcaFlex server:\n" + stderr)

if __name__ == "__main__":
    pass
