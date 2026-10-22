"""Pipe connectivity and supply temperatures."""


class Network:
    def __init__(self, data):
        self.nodes = data['nodes']
        self.ends = [(p['a'], p['b']) for p in data['pipes']]

    def mix(self, states, control):
        rates = [float(x['rate']) for x in control['injection']]
        heat = [x['rate'] * x['temperature'] for x in control['injection']]
        for state, flow, (_, receiver) in zip(states, control['flows'], self.ends):
            rates[receiver] += abs(flow)
            heat[receiver] += abs(flow) * state.temperature
        return [h / q if q else None for h, q in zip(heat, rates)]

    def inlets(self, mixtures):
        return [mixtures[a] for a, _ in self.ends]
