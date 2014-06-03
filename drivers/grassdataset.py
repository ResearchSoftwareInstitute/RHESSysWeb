from ga_resources import drivers, models
from uuid import uuid4
from osgeo import gdal, ogr, osr
from django.conf import settings
from django.contrib.gis.geos import Polygon
import importlib
import os
import sh
import sys

from collections import namedtuple

import tempfile

GRASSEnv = namedtuple('GRASSEnv', ['database', 'location', 'map_set', 'default_raster'], verbose=False)

class GrassMixin(object):
    def __init__(self, env):
        self.env = env
        self.ensure_grass()

    def ensure_grass(self):
        if 'GISRC' not in os.environ:
            grassLib = os.path.join(settings.GISBASE, 'lib')
            os.environ['LD_LIBRARY_PATH'] = ':'.join([os.environ['LD_LIBRARY_PATH'], grassLib])
            os.putenv("LD_LIBRARY_PATH",':'.join([os.environ['LD_LIBRARY_PATH'], grassLib]))
            os.environ['DYLD_LIBRARY_PATH'] = grassLib
            os.putenv("DYLD_LIBRARY_PATH", grassLib)
            os.environ['GIS_LOCK'] = str(os.getpid())
            os.putenv('GIS_LOCK',str(os.getpid()))
            os.environ['GISRC'] = self._initializeGrassrc()
            os.putenv('GISRC', os.environ['GISRC'])

        if 'LOCATION_NAME' not in os.environ:
            os.environ['LOCATION_NAME'] = self.env.location
            os.putenv('LOCATION_NAME', self.env.location)

        if not hasattr(self, '_gsetup'):
            sys.path.append( os.path.join(settings.GISBASE, 'etc', 'python') )
            self._gsetup = importlib.import_module('grass.script.setup')
            self.g = importlib.import_module("grass.script")
            self.grass_lowlevel = importlib.import_module('grass.lib.gis')

        self.grass_lowlevel.G_gisinit('')
        self._gsetup.init(settings.GISBASE, self.env.database, self.env.location, self.env.map_set)

    def _initializeGrassrc(self):
        grassRcFile = tempfile.NamedTemporaryFile(prefix='grassrc-', delete=False)
        grassRcContent = "GISDBASE: %s\nLOCATION_NAME: %s\nMAPSET: %s\n" % \
            (self.env.database, self.env.location, self.env.map_set)
        grassRcFile.write(grassRcContent)
        return grassRcFile.name

    def get_data_fields(self, **kwargs):
        return self.g.raster.list_pairs('rast')

    @property
    def proj(self):

        if not hasattr(self, '_proj'):
            self._proj = osr.SpatialReference()
            self._proj.ImportFromProj4( self.g.raster.read_command('g.proj', flags='j') )

        return self._proj

    @property
    def region(self):

        if not hasattr(self, '_region'):
            self._region = self.g.region()

        return self._region


    def get_real_srs(self, srs):
        r_srs = osr.SpatialReference()

        if isinstance(srs, basestring):
            if srs.lower().startswith('epsg'):
                srs = int(srs[5:])
                r_srs.ImportFromEPSG(srs)
            else:
                r_srs.ImportFromProj4(srs)
        else:
            r_srs.ImportFromEPSG(srs)

        return r_srs


    def get_data_for_point(self, wherex, wherey, srs, fuzziness=0, **kwargs):
        r_srs = self.get_real_srs(srs)
        xrc = osr.CoordinateTransformation(self.proj, r_srs)
        crx = osr.CoordinateTransformation(r_srs, self.proj)
        self.ensure_grass()

        easting, northing, _ = crx.TransformPoint(wherex, wherey)

        rasters = self.g.list_strings('rast')
        def best_type(k):
            try:
                return int(k)
            except:
                try:
                    return float(k)
                except:
                    return k

        c = []
        c.append(dict(zip(rasters, [
            best_type(k) for k in self.g.read_command('r.what', input=rasters, east_north='{e},{n}'.format(e=easting, n=northing)).strip().split('|')
        ])))

        return c

    def ready_data_resource(self, **kwargs):
        print "ready data resource"
        r = self.region
        s_srs =  self.proj
        print s_srs
        print s_srs.ExportToProj4()

        e3857 = osr.SpatialReference()
        e3857.ImportFromEPSG(3857)
        crx = osr.CoordinateTransformation(s_srs, e3857)

        x0, y0, x1, y1 = r['w'], r['s'], r['e'], r['n']
        self.resource.spatial_metadata.native_srs = s_srs.ExportToProj4()

        xx0, yy0, _ = crx.TransformPoint(x0, y0)
        xx1, yy1, _ = crx.TransformPoint(x1, y1)

        raster = kwargs['RASTER'] if 'RASTER' in kwargs else self.env.default_raster
        cached_basename = os.path.join(self.cache_path, raster)
        cached_tiff = cached_basename + '.tif'
        output = cached_basename + '.native.tif'
        output_prj = cached_basename+ '.native.prj'

        # TODO change this to make more sense.
        if not os.path.exists(cached_tiff):
            # Remove GRASS mask if present
            self.g.run_command('r.mask', flags='r')

            mask = kwargs.get('mask', None)
            export = uuid4().hex
            if mask:
                # Use mask to properly set alpha channel of exported TIFF
                self.g.write_command('r.mapcalc', stdin="{export}=if({mask},{raster},{mask})".format(export=export, mask=mask, raster=raster) )
                self.g.run_command('r.out.gdal', flags='f', type='UInt16', input=export, output=output)
            else:
                self.g.run_command('r.out.gdal', flags='f', type='UInt16', input=raster, output=output)

            with open(output_prj, 'w') as prj:
                prj.write(s_srs.ExportToWkt())

            sh.gdalwarp("-s_srs", output_prj, "-t_srs", "EPSG:3857", output, cached_tiff, '-srcnodata', '0', '-dstalpha')

            if export:
                # Clean up temporary export raster
                self.g.run_command('g.remove', rast=export)

        return self.cache_path, (
            self.resource.slug,
            e3857.ExportToProj4(),
            {
                "type" : "gdal",
                "file" : cached_tiff,
            }
        )


class Grass(drivers.Driver):
    ''' TODO: refactor to use GrassMixin
    '''
    def __init__(self, resource):
        super(Grass, self).__init__(data_resource=resource)
        self.env = self.resource.parent.grassenvironment
        self.ensure_grass()

    def ensure_grass(self):
        if 'GISRC' not in os.environ:
            os.environ['LD_LIBRARY_PATH'] = ':'.join([os.environ['LD_LIBRARY_PATH'], "/usr/lib/grass64/lib"])
            os.putenv("LD_LIBRARY_PATH",':'.join([os.environ['LD_LIBRARY_PATH'], "/usr/lib/grass64/lib"]))
            os.environ['DYLD_LIBRARY_PATH'] = os.path.join(settings.GISBASE, 'lib')
            os.putenv("DYLD_LIBRARY_PATH", os.path.join(settings.GISBASE, "lib"))
            os.environ['GIS_LOCK'] = str(os.getpid())
            os.putenv('GIS_LOCK',str(os.getpid()))
            os.environ['GISRC'] = self._initializeGrassrc()
            os.putenv('GISRC', os.environ['GISRC'])

        if 'LOCATION_NAME' not in os.environ:
            os.environ['LOCATION_NAME'] = self.env.location
            os.putenv('LOCATION_NAME', self.env.location)

        if not hasattr(self, '_gsetup'):
            self._gsetup = importlib.import_module('grass.script.setup')
            self.g = importlib.import_module("grass.script")
            self.grass_lowlevel = importlib.import_module('grass.lib.gis')

        self.grass_lowlevel.G_gisinit('')
        self._gsetup.init(settings.GISBASE, self.env.database, self.env.location, self.env.map_set)

    def _initializeGrassrc(self):
        grassRcFile = tempfile.NamedTemporaryFile(prefix='grassrc-', delete=False)
        grassRcContent = "GISDBASE: %s\nLOCATION_NAME: %s\nMAPSET: %s\n" % \
            (self.env.database, self.env.location, self.env.map_set)
        grassRcFile.write(grassRcContent)
        return grassRcFile.name

    def get_data_fields(self, **kwargs):
        return self.g.raster.list_pairs('rast')

    @property
    def proj(self):

        if not hasattr(self, '_proj'):
            self._proj = osr.SpatialReference()
            self._proj.ImportFromProj4( self.g.raster.read_command('g.proj', flags='j') )

        return self._proj

    @property
    def region(self):

        if not hasattr(self, '_region'):
            self._region = self.g.region()

        return self._region

    def get_real_srs(self, srs):
        r_srs = osr.SpatialReference()

        if isinstance(srs, basestring):
            if srs.lower().startswith('epsg'):
                srs = int(srs[5:])
                r_srs.ImportFromEPSG(srs)
            else:
                r_srs.ImportFromProj4(srs)
        else:
            r_srs.ImportFromEPSG(srs)

        return r_srs


    def get_data_for_point(self, wherex, wherey, srs, fuzziness=0, **kwargs):
        r_srs = self.get_real_srs(srs)
        xrc = osr.CoordinateTransformation(self.proj, r_srs)
        crx = osr.CoordinateTransformation(r_srs, self.proj)
        self.ensure_grass()

        easting, northing, _ = crx.TransformPoint(wherex, wherey)

        rasters = self.g.list_strings('rast')
        def best_type(k):
            try:
                return int(k)
            except:
                try:
                    return float(k)
                except:
                    return k

        c = []
        c.append(dict(zip(rasters, [
            best_type(k) for k in self.g.read_command('r.what', input=rasters, east_north='{e},{n}'.format(e=easting, n=northing)).strip().split('|')
        ])))

        return c

    def get_metadata(self, **kwargs):
        return []

    def compute_fields(self, **kwargs):

        r = self.region
        s_srs =  self.proj.ExportToProj4()

        e4326 = osr.SpatialReference()
        e4326.ImportFromEPSG(4326)
        crx = osr.CoordinateTransformation(self.proj, e4326)

        x0, y0, x1, y1 = r['w'], r['s'], r['e'], r['n']
        self.resource.spatial_metadata.native_srs = s_srs

        xx0, yy0, _ = crx.TransformPoint(r['w'], r['s'])
        xx1, yy1, _ = crx.TransformPoint(r['e'], r['n'])
        self.resource.spatial_metadata.native_bounding_box = Polygon.from_bbox((x0, y0, x1, y1))
        self.resource.spatial_metadata.bounding_box = Polygon.from_bbox((xx0, yy0, xx1, yy1))
        self.resource.spatial_metadata.three_d = False
        self.resource.spatial_metadata.save()

    def ready_data_resource(self, **kwargs):
        print "ready data resource"
        r = self.region
        s_srs =  self.proj
        print s_srs
        print s_srs.ExportToProj4()

        e3857 = osr.SpatialReference()
        e3857.ImportFromEPSG(3857)
        crx = osr.CoordinateTransformation(s_srs, e3857)

        x0, y0, x1, y1 = r['w'], r['s'], r['e'], r['n']
        self.resource.spatial_metadata.native_srs = s_srs.ExportToProj4()

        xx0, yy0, _ = crx.TransformPoint(x0, y0)
        xx1, yy1, _ = crx.TransformPoint(x1, y1)

        raster = kwargs['RASTER'] if 'RASTER' in kwargs else self.env.default_raster
        cached_basename = os.path.join(self.cache_path, raster)
        cached_tiff = cached_basename + '.tif'
        output = cached_basename + '.native.tif'
        output_prj = cached_basename+ '.native.prj'

        # TODO change this to make more sense.
        if not os.path.exists(cached_tiff):
            # Remove GRASS mask if present
            self.g.run_command('r.mask', flags='r')

            mask = kwargs.get('mask', None)
            export = uuid4().hex
            if mask:
                # Use mask to properly set alpha channel of exported TIFF
                self.g.write_command('r.mapcalc', stdin="{export}=if({mask},{raster},{mask})".format(export=export, mask=mask, raster=raster) )
                self.g.run_command('r.out.gdal', flags='f', type='UInt16', input=export, output=output)
            else:
                self.g.run_command('r.out.gdal', flags='f', type='UInt16', input=raster, output=output)
                
            with open(output_prj, 'w') as prj:
                prj.write(s_srs.ExportToWkt())

            sh.gdalwarp("-s_srs", output_prj, "-t_srs", "EPSG:3857", output, cached_tiff, '-srcnodata', '0', '-dstalpha')

            if export:
                # Clean up temporary export raster
                self.g.run_command('g.remove', rast=export)

        return self.cache_path, (
            self.resource.slug,
            e3857.ExportToProj4(),
            {
                "type" : "gdal",
                "file" : cached_tiff,
            }
        )

driver = Grass
