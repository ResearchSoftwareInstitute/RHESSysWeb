
import os, sys
from zipfile import ZipFile
from shutil import rmtree
from collections import namedtuple

from unittest import TestCase

import logging

from RHESSysWeb.worldfileio import *

GRASSEnv = namedtuple('GRASSEnv', ['database', 'location', 'map_set', 'default_raster'], verbose=False)

class TestWorldfileIO(TestCase):
    """ To Run:

    GISBASE=/usr/lib/grass64 LD_LIBRARY_PATH=$GISBASE/lib python -m nose RHESSysWeb.tests.test_worldfileio
    """

    @classmethod
    def setupClass(cls):
        testDir = os.path.dirname(os.path.realpath(__file__))
        extractDir = os.path.abspath( os.path.join(testDir, 'data'))
        testDataDirName = 'EllerbeCk_ClubBlvd'
        cls.testDataDirPath = os.path.join(extractDir, testDataDirName)

        testDataZipName = "%s.zip" % (testDataDirName,)
        testDataZipPath = os.path.join(extractDir, testDataZipName)
        zip = ZipFile(testDataZipPath, 'r')
        zip.extractall(path=extractDir)

        grassEnv = GRASSEnv
        grassEnv.location = 'default'
        grassEnv.map_set = 'PERMANENT'
        grassEnv.database = os.path.join(extractDir, testDataDirName, 'GRASSData')
        grassEnv.default_raster = 'landcover'
        cls.grassEnv = grassEnv

        cls.templatePath = os.path.join(cls.testDataDirPath, 'rhessys', 'templates', 'template')

    def setUp(self):
        self.logger = logging.getLogger(__name__)
        stream_handler = logging.StreamHandler(sys.stderr)
        self.logger.addHandler(stream_handler)

    @classmethod
    def tearDownClass(cls):
        rmtree(cls.testDataDirPath)

    def test_template(self):
        worldfile = WorldfileIO(self.templatePath, self.grassEnv)

        extentOne = 0
        basinAttr = worldfile.templateLevels['basin'].attributes[extentOne]
        self.assertTrue(basinAttr['latitude'].value == 36.02982)

        self.assertTrue(worldfile.templateLevels['patch'].map == 'patch')
        patchAttr = worldfile.templateLevels['patch'].attributes[extentOne]
        soil = patchAttr['soil_default']
        self.assertTrue(soil.map == 'soil_texture')
        self.assertTrue(isinstance(soil, TemplateFunctionMode))
        a_area = patchAttr['a_area']
        self.assertTrue(isinstance(a_area, TemplateFunctionArea))
        self.assertIsNone(a_area.map)

        self.assertTrue(worldfile.templateLevels['stratum'].map == 'patch')
        stratumAttr = worldfile.templateLevels['stratum'].attributes[extentOne]
        stratum = stratumAttr['default_ID']
        self.assertTrue(stratum.map == 'stratum')
        self.assertTrue(isinstance(stratum, TemplateFunctionMode))

        self.assertTrue(True)