
from ga_resources import drivers
from grassdataset import GrassMixin

from RHESSysWeb.worldfileio import WorldfileIO

class WorldfileDriver(GrassMixin, drivers.Driver):
    def __init__(self, resource, template, logger=None):
        drivers.Driver.__init__(self, data_resource=resource)
        GrassMixin.__init__(self, env=resource.parent.grassenvironment)

        self.template = template
        self.logger = logger

        if self.logger:
            logger.debug("GRASS database: {0}, RHESSys template: {1}".format(self.env.database, self.template) )

        self.worldfile = WorldfileIO(self.template, self.env, self.logger)
