
import os

level_indicator = '_'
levels = ['world', 'basin', 'hillslope', 'zone', 'patch', 'stratum']
header_levels = ['basin', 'hillslope', 'zone', 'soil', 'landuse', 'stratum']
clim = 'clim'

class TemplateFunction(object):
    num_elem = 1

    def __init__(self, elem):
        if len(elem) != self.num_elem:
            raise Exception("Expected {0} elements but received {1}".format(self.num_elem, len(elem)))
        self.map = None

    @classmethod
    def createFunctions(cls, extent, elem):
        ''' Factory method for creating specific functions from template file input

        Parameters:
        extent -- Integer representing number of functions expected in line
        elem -- List of strings representing tokens of functions

            Returns a list, of length extent, containing functions defined in a line.
        '''
        ret = []

        # Choose our function
        functype = elem[0]
        elem = elem[1:]
        if functype == TemplateFunctionAver.functype:
            function = TemplateFunctionAver
        elif functype == TemplateFunctionDAver.functype:
            function = TemplateFunctionDAver
        elif functype == TemplateFunctionArea.functype:
            function = TemplateFunctionArea
        elif functype == TemplateFunctionCount.functype:
            function = TemplateFunctionCount
        elif functype == TemplateFunctionEqn.functype:
            function = TemplateFunctionEqn
        elif functype == TemplateFunctionDEqn.functype:
            function = TemplateFunctionDEqn
        elif functype == TemplateFunctionValue.functype:
            function = TemplateFunctionValue
        elif functype == TemplateFunctionDValue.functype:
            function = TemplateFunctionDValue
        elif functype == TemplateFunctionSPAvg.functype:
            function = TemplateFunctionSPAvg
        elif functype == TemplateFunctionMode.functype:
            function = TemplateFunctionMode
        else:
            raise Exception("Unknown template function type '{0}' encountered".format(functype))

        # Make sure we have enough elements to make our function(s)
        if len(elem) != function.num_elem * extent:
            raise Exception("Expected {0} elements for function {1} with extent {2}, but only found {3}".
                            format(function.num_elem * extent, functype, extent, len(elem)))

        # Make extent number of functions
        for i in range(extent):
            j = i + function.num_elem
            ret.append(function(elem[i:j]))

        return ret

class TemplateFunctionAver(TemplateFunction):
    functype = 'aver'
    num_elem = 1

    def __init__(self, elem):
        super(TemplateFunctionAver, self).__init__(elem)
        self.map = elem[0]

class TemplateFunctionDAver(TemplateFunction):
    functype = 'daver'
    num_elem = 1

    def __init__(self, elem):
        super(TemplateFunctionDAver, self).__init__(elem)
        self.map = elem[0]

class TemplateFunctionArea(TemplateFunction):
    functype = 'area'
    num_elem = 0

    def __init__(self, elem):
        super(TemplateFunctionArea, self).__init__(elem)

class TemplateFunctionCount(TemplateFunction):
    functype = 'count'
    num_elem = 1

    def __init__(self, elem):
        super(TemplateFunctionCount, self).__init__(elem)
        self.map = elem[0]

class TemplateFunctionEqn(TemplateFunction):
    functype = 'eqn'
    num_elem = 3

    def __init__(self, elem):
        super(TemplateFunctionEqn, self).__init__(elem)
        self.mult = float(elem[0])
        self.add = float(elem[1])
        self.map = elem[2]

class TemplateFunctionDEqn(TemplateFunction):
    functype = 'deqn'
    num_elem = 3

    def __init__(self, elem):
        super(TemplateFunctionDEqn, self).__init__(elem)
        self.mult = float(elem[0])
        self.add = float(elem[1])
        self.map = elem[2]

class TemplateFunctionValue(TemplateFunction):
    functype = 'value'
    num_elem = 1

    def __init__(self, elem):
        super(TemplateFunctionValue, self).__init__(elem)
        self.value = float(elem[0])

class TemplateFunctionDValue(TemplateFunction):
    functype = 'dvalue'
    num_elem = 1

    def __init__(self, elem):
        super(TemplateFunctionDValue, self).__init__(elem)
        self.value = int(elem[0])

class TemplateFunctionSPAvg(TemplateFunction):
    functype = 'spavg'
    num_elem = 2

    def __init__(self, elem):
        super(TemplateFunctionSPAvg, self).__init__(elem)
        self.map = elem[0]
        self.map2 = elem[1]

class TemplateFunctionMode(TemplateFunction):
    functype = 'mode'
    num_elem = 1

    def __init__(self, elem):
        super(TemplateFunctionMode, self).__init__(elem)
        self.map = elem[0]


class TemplateLevel(object):
    def __init__(self, name, map, extent):
        self.name = name
        self.map = map
        self.extent = extent
        self.attributes = [dict() for i in range(extent)]

    def __str__(self):
        return "TemplateLevel, name: {name}, map: {map}, extent: {extent}, attributes: {attributes}".\
            format(name=self.name, map=self.map, extent=self.extent,
                   attributes=str(self.attributes))


class WorldfileIO(object):

    def __init__(self, templatePath, grassEnv, logger=None):
        self.templatePath = templatePath
        self.grassEnv = grassEnv
        self.logger = logger

        self.templateLevels = {}
        self.readTemplateFile()


    @classmethod
    def _readTemplateHeader(cls, f):
        ret = {}

        for level in header_levels:
            line = f.readline().strip()
            num_def_files = 0
            try:
                num_def_files = int(line)
            except ValueError:
                raise Exception("Expected an integer when reading number of def files for level {0} but received {1}".
                                format(level, line))

            defs_for_level = None
            try:
                defs_for_level = ret[level]
            except KeyError:
                defs_for_level = []
                ret[level] = defs_for_level

            # Read each def filename
            for i in range(num_def_files):
                line = f.readline().strip()
                # TODO: check to make sure file exists
                defs_for_level.append(line)

        # Read climate stations
        line = f.readline().strip()
        climate_stations = []
        ret[clim] = climate_stations
        num_clim_sta = 0
        try:
            num_clim_sta = int(line)
        except ValueError:
            raise Exception("Expected an integer when reading number of climate stations but received {0}".format(line))
        for i in range(num_clim_sta):
            line = f.readline().strip()
            # TODO: check to make sure file exists
            climate_stations.append(line)

        return ret

    @classmethod
    def _readLevel(cls, level, map, extent, f):
        ret = TemplateLevel(level, map, extent)

        prev_offset = f.tell()
        line = f.readline()
        while line:
            line = line.strip()
            if line == '':
                break

            if line.startswith(level_indicator):
                # We're at another level, undo the read and exit the function
                f.seek(prev_offset)
                break

            elem = line.split()
            if len(elem) <= 1:
                raise Exception("Expected more than one token for line |{0}|".format(line))
            attr = elem[0]

            try:
                functions = TemplateFunction.createFunctions(extent, elem[1:])
            except Exception as e:
                raise Exception("The following error occurred while reading line: {0}.  The error was: {1}".
                                format(line, str(e)))

            # Store function(s) for attribute, one function for each extent
            for i in range(extent):
                extentDict = ret.attributes[i]
                extentDict[attr] = functions[i]

            prev_offset = f.tell()
            line = f.readline()

        return ret



    def readTemplateFile(self):
        if not os.access(self.templatePath, os.R_OK):
            raise IOError("Unable to read template file {0}".format(self.templatePath))

        f = open(self.templatePath, 'r')

        self.header = WorldfileIO._readTemplateHeader(f)
        if self.logger:
            self.logger.debug(str(self.header))

        # Read levels
        line = f.readline()
        while line:
            line = line.strip()

            try:
                (level, map, extent) = line.split()
                if not level.startswith(level_indicator):
                    raise Exception("Expected level indicator (i.e. value starting with '_'), but received {0}".
                                    format(line))
                level = level.split(level_indicator)[-1]
                if level in self.templateLevels:
                    raise Exception("Level {0} has been encountered more than once in template {1}".
                                    format(level, self.templatePath))
                # TODO: make sure map exists in GRASS
                try:
                    extent = int(extent)
                except ValueError:
                    raise Exception("Expected integer extent for level {0}, but received {1}".
                                    format(level, extent))

                self.templateLevels[level] = WorldfileIO._readLevel(level, map, extent, f)
                if self.logger:
                    self.logger.debug(str(self.templateLevels[level]))

            except ValueError:
                raise Exception("Expected line with three space-separated strings, but received {0}".
                                format(line))



            line = f.readline()

        f.close()
