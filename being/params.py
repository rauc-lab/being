from being.block import Block


class Parameter(Block):
    def __init__(self, name, comment=None, configFile=None):
        if configFile is None:
            configFile = ConfigFile.single_instance_setdefault(filepath='being.yaml')

        super().__init__()
        self.add_value_output()
        self.name = name
        self.configFile = configFile
        self.comment = comment

        if comment is None:
            comment = self.configFile.get_comment(self.name)
        else:
            self.configFile.set_comment(self.name, comment)

        value = self.configFile.retrieve(self.name)
        if value is None:
            self.configFile.store(self.name, 0.0)
            self.output.value = 0.0
        else:
            self.output.value = value

    #def on_change(self):
    #    self.config.store(self.name, self.output.value)

    def __str__(self):
        return f'{type(self).__name__}(name: {self.name}, configFile: {self.configFile})'



class Slider(Parameter):
    pass

class Selection(Parameter):
    pass


class Slider(Parameter):
    def __init__(self, name, minValue=0., maxValue=INF, *args, **kwargs):
        assert minValue < maxValue
        super().__init__(name, *args, **kwargs)
        self.minValue = minValue
        self.maxValue = maxValue

        value = self.retrieve_value()
        if value is None:
            self.store_value(self.output.value)
        else:
            self.output.value = value


class Selection(Parameter):
    def __init__(self, name, possibilities=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.possibilities = possibilities
