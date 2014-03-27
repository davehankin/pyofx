import unittest
from __init__ import *
import tempfile
import random

class TestObjectFilter(unittest.TestCase):

    def setUp(self):
        self.m=Model()
        self.line_objects = ['TEST LINE {}'.format(n) for n in range(1,11)]
        self.six_d_objects = ['TEST 6D {}'.format(n) for n in range(1,11)]
        self.shape_objects = ['TEST SHAPE {}'.format(n) for n in range(1,11)]
        for l,b,s in zip(self.line_objects,self.six_d_objects,self.shape_objects):            
            self.m.CreateObject(otLine,name=l)
            self.m.CreateObject(ot6DBuoy,name=b)
            self.m.CreateObject(otShape,name=s)
        

    def test_filter_lines(self):
        self.assertListEqual( [o.Name for o in self.m.objects_of_type("Line")],
                               self.line_objects)

    def test_filter_six_d_buoys(self):
        self.assertListEqual( [o.Name for o in self.m.objects_of_type("6D Buoy")],
                               self.six_d_objects)
        
    def test_filter_shapes(self):
        self.assertListEqual( [o.Name for o in self.m.objects_of_type("Shape")],
                               self.shape_objects)
        
    def test_filter_lines_string_argument(self):
        self.assertListEqual( [o.Name for o in self.m.objects_of_type("Line","6")],
                               ['TEST LINE 6'])
        
    def test_filter_lines_function_argument(self):
        test_function = lambda obj: ("1" in obj.Name) or ("5" in obj.Name)
        self.assertListEqual( [o.Name for o in self.m.objects_of_type("Line",test_function)],
                               ['TEST LINE 1','TEST LINE 5','TEST LINE 10'])

class TestModels(unittest.TestCase):
    
    def setUp(self):
        self._temp_dir1 = tempfile.mkdtemp()
        self._temp_dir2 = tempfile.mkdtemp()
        self._temp_dir3 = tempfile.mkdtemp()
        pass #TODO: COMPLETE THIS

        
        
        
if __name__ == '__main__':
    unittest.main()