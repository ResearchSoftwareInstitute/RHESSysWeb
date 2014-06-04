
import os, sys
from zipfile import ZipFile
from shutil import rmtree
from collections import namedtuple

#import unittest
from django.test import TestCase

import logging

from RHESSysWeb.drivers.grassdataset import GRASSEnv
from RHESSysWeb.drivers.worldfile import WorldfileDriver

from RHESSysWeb.worldfileio import *

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
        cls.resource = dummy_resource(parent=parent, cache_path=cls.testDataDirPath, slug='TestWorldfileDriver slug')

        cls.templatePath = os.path.join(cls.testDataDirPath, 'rhessys', 'templates', 'template')


    def setUp(self):
        self.logger = logging.getLogger(__name__)
        stream_handler = logging.StreamHandler(sys.stderr)
        self.logger.addHandler(stream_handler)

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.testDataDirPath)

    def testTemplate(self):
        worldfileDriver = WorldfileDriver(TestWorldfileDriver.resource, TestWorldfileDriver.templatePath) #, self.logger)

        extentOne = 0
        basinAttr = worldfileDriver.worldfile.templateLevels['basin'].attributes[extentOne]
        self.assertTrue(basinAttr['latitude'].value == 36.02982)

        self.assertTrue(worldfileDriver.worldfile.templateLevels['patch'].map == 'patch')
        patchAttr = worldfileDriver.worldfile.templateLevels['patch'].attributes[extentOne]
        soil = patchAttr['soil_default']
        self.assertTrue(soil.map == 'soil_texture')
        self.assertTrue(isinstance(soil, TemplateFunctionMode))
        a_area = patchAttr['a_area']
        self.assertTrue(isinstance(a_area, TemplateFunctionArea))
        self.assertIsNone(a_area.map)

        self.assertTrue(worldfileDriver.worldfile.templateLevels['stratum'].map == 'patch')
        stratumAttr = worldfileDriver.worldfile.templateLevels['stratum'].attributes[extentOne]
        stratum = stratumAttr['default_ID']
        self.assertTrue(stratum.map == 'stratum')
        self.assertTrue(isinstance(stratum, TemplateFunctionMode))

        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()