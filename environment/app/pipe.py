"""Thermal state of an insulated pipe."""
import math


class Pipe:
    def __init__(self, specification, ambient):
        self.volume = float(specification['volume'])
        self.loss = float(specification['loss'])
        self.ambient = float(ambient)
        self.temperature = sum(part['volume'] * part['temperature']
                               for part in specification['initial']) / self.volume

    def advance(self, minutes, flow, inlet):
        turnover = abs(flow) / self.volume
        if turnover and inlet is not None:
            rate = turnover + self.loss
            equilibrium = (turnover * inlet + self.loss * self.ambient) / rate
            self.temperature = equilibrium + (self.temperature - equilibrium) * math.exp(-rate * minutes)

    def sample(self, position):
        return self.temperature

    def heat(self):
        return 4.18 * self.volume * (self.temperature - self.ambient)
