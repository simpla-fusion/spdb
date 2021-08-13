import importlib
import pprint
import sys
import unittest

from spdm.data.Function import Function
from spdm.data.Node import _next_
from spdm.data.Profiles import Profiles
from spdm.numlib import np
from spdm.util.logger import logger


class TestProfiles(unittest.TestCase):
    def test_profile_initialize(self):
        axis = np.linspace(0, 1, 128)
        cache = {}
        profiles = Profiles(cache, axis=axis)
        profiles["a"] = np.random.rand(128)
        profiles["b"] = 1
     
        self.assertTrue(isinstance(profiles["a"], Function))
        self.assertTrue(isinstance(profiles["b"], int))


if __name__ == '__main__':
    unittest.main()