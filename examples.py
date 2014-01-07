from pyofx import *
from time import sleep

def grab_licence():
    while not check_licence():
        sleep(1)
    Model().open()

grab_licence()