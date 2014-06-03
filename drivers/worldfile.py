
from ga_resources import drivers
from grassdataset import GrassMixin

class WorldfileDriver(GrassMixin, drivers.Driver):
    def __init__(self, resource, template):
        drivers.Driver.__init__(self, data_resource=resource)
        GrassMixin.__init__(self, env=resource.parent.grassenvironment)

        self.template = template

        print self.env.database
        print self.template
