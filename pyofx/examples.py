from pyofx import *
from time import sleep

def grab_licence():
	"""try to open OrcaFlex once a second"""
    while not check_licence():
        sleep(1)
    Model().open()
