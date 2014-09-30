import unittest
from __init__ import *
import tempfile
import random
from os import path
import shutil
from itertools import product


class TestModelAttributes(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.mkdtemp()
        self._model_name = "Temp Model"

    def test_path_attributes(self):
        self.dat, self.sim = dat_sim_paths(self._temp_dir, self._model_name)
        m = Model()
        m.SaveData(self.dat)
        self.assertEqual(m.path, self.dat)
        self.assertEqual(self._model_name, m.model_name)
        del m
        m = Model(self.dat)
        self.assertEqual(m.path, self.dat)
        self.assertEqual(self._model_name, m.model_name)
        m.general.StageDuration = [1, 1]
        m.RunSimulation()
        m.SaveSimulation(self.sim)
        self.assertEqual(m.path, self.sim)
        self.assertEqual(self._model_name, m.model_name)
        del m
        m = Model(self.sim)
        self.assertEqual(m.path, self.sim)
        self.assertEqual(self._model_name, m.model_name)


class TestObjectFilter(unittest.TestCase):

    def setUp(self):
        self.m = Model()
        self.line_objects = ['TEST LINE {}'.format(n) for n in range(1, 11)]
        self.six_d_objects = ['TEST 6D {}'.format(n) for n in range(1, 11)]
        self.shape_objects = ['TEST SHAPE {}'.format(n) for n in range(1, 11)]
        self.vessel_objects = [
            'TEST VESSEL {}'.format(n) for n in range(1, 11)]

        for l, b, v, s in zip(self.line_objects, self.six_d_objects,
                              self.vessel_objects, self.shape_objects):
            self.m.CreateObject(otLine, name=l)
            self.m.CreateObject(ot6DBuoy, name=b)
            self.m.CreateObject(otShape, name=s)
            self.m.CreateObject(otVessel, name=v)

    def test_filter_lines(self):
        self.assertListEqual([o.Name for o in self.m.objects_of_type("Line")],
                             self.line_objects)
        self.assertListEqual([o.Name for o in self.m.lines],
                             self.line_objects)

    def test_filter_vessels(self):
        self.assertListEqual(
            [o.Name for o in self.m.objects_of_type("Vessel")],
            self.vessel_objects)
        self.assertListEqual([o.Name for o in self.m.vessels],
                             self.vessel_objects)

    def test_filter_six_d_buoys(self):
        self.assertListEqual(
            [o.Name for o in self.m.objects_of_type("6D Buoy")],
            self.six_d_objects)
        self.assertListEqual([o.Name for o in self.m.six_d_buoys],
                             self.six_d_objects)

    def test_filter_shapes(self):
        self.assertListEqual([o.Name for o in self.m.objects_of_type("Shape")],
                             self.shape_objects)

    def test_filter_lines_string_argument(self):
        self.assertListEqual(
            [o.Name for o in self.m.objects_of_type("Line", "6")],
            ['TEST LINE 6'])

    def test_filter_lines_function_argument(self):
        test_function = lambda obj: ("1" in obj.Name) or ("5" in obj.Name)
        self.assertListEqual(
            [o.Name for o in self.m.objects_of_type("Line", test_function)],
            ['TEST LINE 1', 'TEST LINE 5', 'TEST LINE 10'])


class TestModels(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self._temp_dir1 = tempfile.mkdtemp()
        self._temp_dir2 = tempfile.mkdtemp()
        self._temp_dir3 = tempfile.mkdtemp()
        self._temp_dirs = [self._temp_dir1, self._temp_dir2, self._temp_dir3]

        for d, n in product(self._temp_dirs, range(1)):
            print "Build model {} in {}".format(n, d)
            m = Model()
            m.general.StageDuration = [1, 2]
            m.general.ImplicitConstantTimeStep = 1
            m.SaveData(path.join(d, "unittest_case_{}.dat".format(n)))
            m.RunSimulation()
            m.SaveSimulation(path.join(d, "unittest_case_{}.sim".format(n)))

    @classmethod
    def tearDownClass(self):
        for dir_ in self._temp_dirs:
            shutil.rmtree(dir_)

    def test_one_dir_return_dat_model(self):
        for m in Models(self._temp_dir1):
            self.assertIsInstance(m, Model)
            self.assertTrue(m.path.endswith('.dat'))

    def test_one_dir_return_sim_model(self):
        for m in Models(self._temp_dir2, filetype="sim"):
            self.assertIsInstance(m, Model)
            self.assertTrue(m.path.endswith('.sim'))

    def test_one_dir_return_dat_path(self):
        for m in Models(self._temp_dir1, return_model=False):
            self.assertIsInstance(m, str)
            self.assertTrue(path.exists(m))
            self.assertTrue(m.endswith('.dat'))

    def test_one_dir_return_sim_path(self):
        for m in Models(self._temp_dir2,
                        filetype="sim", return_model=False):
            self.assertIsInstance(m, str)
            self.assertTrue(path.exists(m))
            self.assertTrue(m.endswith('.sim'))

    def test_one_dir_return_sim_use_virtual(self):
        for m in Models(self._temp_dir2,
                        filetype="sim", virtual_logging=True):
            self.assertIsInstance(m, Model)
            with self.assertRaises(DLLError):
                m.RunSimulation()


if __name__ == '__main__':
    import sys
    if check_licence:
        current_module = sys.modules[__name__]
        test_suite = unittest.loader.findTestCases(current_module)
        runner = unittest.TextTestRunner()
        runner.run(test_suite)
    else:
        raise Exception("No OrcaFlex License!")
