#!/usr/bin/python2

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for bisecting tool."""

from __future__ import print_function

__author__ = 'shenhan@google.com (Han Shen)'

import os
import random
import sys
import unittest

from utils import command_executer
from binary_search_tool import binary_search_state
from binary_search_tool import bisect

import common
import gen_obj


def GenObj():
  obj_num = random.randint(100, 1000)
  bad_obj_num = random.randint(obj_num / 100, obj_num / 20)
  if bad_obj_num == 0:
    bad_obj_num = 1
  gen_obj.Main(['--obj_num', str(obj_num), '--bad_obj_num', str(bad_obj_num)])


def CleanObj():
  os.remove(common.OBJECTS_FILE)
  os.remove(common.WORKING_SET_FILE)
  print('Deleted "{0}" and "{1}"'.format(common.OBJECTS_FILE,
                                         common.WORKING_SET_FILE))


class BisectTest(unittest.TestCase):
  """Tests for bisect.py"""

  def setUp(self):
    with open('./installed', 'w'):
      pass

    try:
      os.remove(binary_search_state.STATE_FILE)
    except OSError:
      pass

  def tearDown(self):
    try:
      os.remove('./installed')
      os.remove(os.readlink(binary_search_state.STATE_FILE))
      os.remove(binary_search_state.STATE_FILE)
    except OSError:
      pass

  class FullBisector(bisect.Bisector):
    """Test bisector to test bisect.py with"""

    def __init__(self, options, overrides):
      super(BisectTest.FullBisector, self).__init__(options, overrides)

    def PreRun(self):
      GenObj()
      return 0

    def Run(self):
      return binary_search_state.Run(get_initial_items='./gen_init_list.py',
                                     switch_to_good='./switch_to_good.py',
                                     switch_to_bad='./switch_to_bad.py',
                                     test_script='./is_good.py',
                                     prune=True,
                                     file_args=True)

    def PostRun(self):
      CleanObj()
      return 0

  def test_full_bisector(self):
    ret = bisect.Run(self.FullBisector({}, {}))
    self.assertEquals(ret, 0)
    self.assertFalse(os.path.exists(common.OBJECTS_FILE))
    self.assertFalse(os.path.exists(common.WORKING_SET_FILE))

  def check_output(self):
    _, out, _ = command_executer.GetCommandExecuter().RunCommandWOutput(
        ('grep "Bad items are: " logs/binary_search_tool_tester.py.out | '
         'tail -n1'))
    ls = out.splitlines()
    self.assertEqual(len(ls), 1)
    line = ls[0]

    _, _, bad_ones = line.partition('Bad items are: ')
    bad_ones = bad_ones.split()
    expected_result = common.ReadObjectsFile()

    # Reconstruct objects file from bad_ones and compare
    actual_result = [0] * len(expected_result)
    for bad_obj in bad_ones:
      actual_result[int(bad_obj)] = 1

    self.assertEqual(actual_result, expected_result)


class BisectingUtilsTest(unittest.TestCase):
  """Tests for bisecting tool."""

  def setUp(self):
    """Generate [100-1000] object files, and 1-5% of which are bad ones."""
    GenObj()

    with open('./installed', 'w'):
      pass

    try:
      os.remove(binary_search_state.STATE_FILE)
    except OSError:
      pass

  def tearDown(self):
    """Cleanup temp files."""
    CleanObj()

    try:
      os.remove('./installed')
      os.remove(os.readlink(binary_search_state.STATE_FILE))
      os.remove(binary_search_state.STATE_FILE)
    except OSError:
      pass

  def runTest(self):
    ret = binary_search_state.Run(get_initial_items='./gen_init_list.py',
                                  switch_to_good='./switch_to_good.py',
                                  switch_to_bad='./switch_to_bad.py',
                                  test_script='./is_good.py',
                                  prune=True,
                                  file_args=True)
    self.assertEquals(ret, 0)
    self.check_output()

  def test_arg_parse(self):
    args = ['--get_initial_items', './gen_init_list.py', '--switch_to_good',
            './switch_to_good.py', '--switch_to_bad', './switch_to_bad.py',
            '--test_script', './is_good.py', '--prune', '--file_args']
    ret = binary_search_state.Main(args)
    self.assertEquals(ret, 0)
    self.check_output()

  def test_install_script(self):
    os.remove('./installed')
    with self.assertRaises(AssertionError):
      ret = binary_search_state.Run(get_initial_items='./gen_init_list.py',
                                    switch_to_good='./switch_to_good.py',
                                    switch_to_bad='./switch_to_bad.py',
                                    test_script='./is_good.py',
                                    prune=True,
                                    file_args=True)

    ret = binary_search_state.Run(get_initial_items='./gen_init_list.py',
                                  switch_to_good='./switch_to_good.py',
                                  switch_to_bad='./switch_to_bad.py',
                                  test_script='./is_good.py',
                                  install_script='./install.py',
                                  prune=True,
                                  file_args=True)
    self.assertEquals(ret, 0)
    self.check_output()

  def test_bad_install_script(self):
    with self.assertRaises(AssertionError):
      binary_search_state.Run(get_initial_items='./gen_init_list.py',
                              switch_to_good='./switch_to_good.py',
                              switch_to_bad='./switch_to_bad.py',
                              test_script='./is_good.py',
                              install_script='./install_bad.py',
                              prune=True,
                              file_args=True)

  def test_bad_save_state(self):
    state_file = binary_search_state.STATE_FILE
    hidden_state_file = os.path.basename(binary_search_state.HIDDEN_STATE_FILE)

    with open(state_file, 'w') as f:
      f.write('test123')

    bss = binary_search_state.MockBinarySearchState()
    with self.assertRaises(binary_search_state.Error):
      bss.SaveState()

    with open(state_file, 'r') as f:
      self.assertEquals(f.read(), 'test123')

    os.remove(state_file)

    # Cleanup generated save state that has no symlink
    files = os.listdir(os.getcwd())
    save_states = [x for x in files if x.startswith(hidden_state_file)]
    _ = [os.remove(x) for x in save_states]

  def test_save_state(self):
    state_file = binary_search_state.STATE_FILE

    bss = binary_search_state.MockBinarySearchState()
    bss.SaveState()
    self.assertTrue(os.path.exists(state_file))
    first_state = os.readlink(state_file)

    bss.SaveState()
    second_state = os.readlink(state_file)
    self.assertTrue(os.path.exists(state_file))
    self.assertTrue(second_state != first_state)
    self.assertFalse(os.path.exists(first_state))

    bss.RemoveState()
    self.assertFalse(os.path.islink(state_file))
    self.assertFalse(os.path.exists(second_state))

  def test_load_state(self):
    test_items = [1, 2, 3, 4, 5]

    bss = binary_search_state.MockBinarySearchState()
    bss.all_items = test_items
    bss.SaveState()

    bss = None

    bss2 = binary_search_state.MockBinarySearchState.LoadState()
    self.assertEquals(bss2.all_items, test_items)

  def test_tmp_cleanup(self):
    bss = binary_search_state.MockBinarySearchState(
        get_initial_items='echo "0\n1\n2\n3"',
        switch_to_good='./switch_tmp.py',
        file_args=True)
    bss.SwitchToGood(['0', '1', '2', '3'])

    tmp_file = None
    with open('tmp_file', 'r') as f:
      tmp_file = f.read()
    os.remove('tmp_file')

    self.assertFalse(os.path.exists(tmp_file))
    ws = common.ReadWorkingSet()
    for i in range(3):
      self.assertEquals(ws[i], 42)

  def test_verify_fail(self):
    bss = binary_search_state.MockBinarySearchState(
        get_initial_items='./gen_init_list.py',
        switch_to_good='./switch_to_bad.py',
        switch_to_bad='./switch_to_good.py',
        test_script='./is_good.py',
        prune=True,
        file_args=True,
        verify_level=1)
    with self.assertRaises(AssertionError):
      bss.DoVerify()

  def test_early_terminate(self):
    bss = binary_search_state.MockBinarySearchState(
        get_initial_items='./gen_init_list.py',
        switch_to_good='./switch_to_good.py',
        switch_to_bad='./switch_to_bad.py',
        test_script='./is_good.py',
        prune=True,
        file_args=True,
        iterations=1)
    bss.DoSearch()
    self.assertFalse(bss.found_items)

  def check_output(self):
    _, out, _ = command_executer.GetCommandExecuter().RunCommandWOutput(
        ('grep "Bad items are: " logs/binary_search_tool_tester.py.out | '
         'tail -n1'))
    ls = out.splitlines()
    self.assertEqual(len(ls), 1)
    line = ls[0]

    _, _, bad_ones = line.partition('Bad items are: ')
    bad_ones = bad_ones.split()
    expected_result = common.ReadObjectsFile()

    # Reconstruct objects file from bad_ones and compare
    actual_result = [0] * len(expected_result)
    for bad_obj in bad_ones:
      actual_result[int(bad_obj)] = 1

    self.assertEqual(actual_result, expected_result)


def Main(argv):
  num_tests = 2
  if len(argv) > 1:
    num_tests = int(argv[1])

  suite = unittest.TestSuite()
  for _ in range(0, num_tests):
    suite.addTest(BisectingUtilsTest())
  suite.addTest(BisectingUtilsTest('test_arg_parse'))
  suite.addTest(BisectingUtilsTest('test_install_script'))
  suite.addTest(BisectingUtilsTest('test_bad_install_script'))
  suite.addTest(BisectingUtilsTest('test_bad_save_state'))
  suite.addTest(BisectingUtilsTest('test_save_state'))
  suite.addTest(BisectingUtilsTest('test_load_state'))
  suite.addTest(BisectingUtilsTest('test_tmp_cleanup'))
  suite.addTest(BisectingUtilsTest('test_verify_fail'))
  suite.addTest(BisectingUtilsTest('test_early_terminate'))
  suite.addTest(BisectTest('test_full_bisector'))
  runner = unittest.TextTestRunner()
  runner.run(suite)


if __name__ == '__main__':
  Main(sys.argv)
