
import os
from zipfile import ZipFile
from shutil import rmtree
from collections import namedtuple

#import unittest
from django.test import TestCase

from RHESSysWeb.drivers.grassdataset import GRASSEnv
from RHESSysWeb.drivers.worldfile import WorldfileDriver

dummy_resource = namedtuple('dummy_resource', ['parent', 'cache_path', 'slug'], verbose=False)
dummy_parent = namedtuple('dummy_parent', ['grassenvironment'], verbose=False)

class TestWorldfileDriver(TestCase):
    ''' To Run:

    If within docker, first do:

    export LOCALE='C'
    export LC_ALL='C'
    export LANG='en.US-UTF8'
    export ENCODING='US-ASCII'

    Configure settings.py:

    GISBASE = '/usr/lib/grass64'

    Then (or if not in docker):

    GISBASE=/usr/lib/grass64 LD_LIBRARY_PATH=$GISBASE/lib python manage.py test RHESSysWeb.tests.test_worldfile_driver
    '''

    @classmethod
    def setupClass(cls):
        testDir = os.path.dirname( os.path.realpath(__file__) )
        extractDir = os.path.abspath( os.path.join(testDir, 'data') )
        testDataDirName = 'EllerbeCk_ClubBlvd'
        cls.testDataDirPath = os.path.join(extractDir, testDataDirName)

        testDataZipName = "%s.zip" % (testDataDirName,)
        testDataZipPath = os.path.join(extractDir, testDataZipName)
        zip = ZipFile(testDataZipPath, 'r')
        zip.extractall(path=extractDir)

#        gisbase = os.environ['GISBASE']
        grassEnv = GRASSEnv
        grassEnv.location = 'default'
        grassEnv.map_set = 'PERMANENT'
        grassEnv.database = os.path.join(extractDir, testDataDirName, 'GRASSData')
        grassEnv.default_raster = 'landcover'
        parent = dummy_parent(grassenvironment=grassEnv)
        resource = dummy_resource(parent=parent, cache_path=cls.testDataDirPath, slug='TestWorldfileDriver slug')

        templatePath = os.path.join(cls.testDataDirPath, 'rhessys', 'templates', 'template')

        cls.worldfileDriver = WorldfileDriver(resource, templatePath)

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.testDataDirPath)

    def testDummy(self):
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()