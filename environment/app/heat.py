#!/usr/bin/env python3
"""Command-line report for a district heating network."""
import bisect
import json
import os
import sys
import tempfile

from network import Network
from pipe import Pipe


def simulate(data):
    network = Network(data)
    states = [Pipe(p, data['ambient']) for p in data['pipes']]
    controls = data['controls']
    times = [c['time'] for c in controls]
    now = 0.0
    snapshots = [None] * len(data['queries'])
    for index in sorted(range(len(snapshots)), key=lambda i: data['queries'][i]['time']):
        query = data['queries'][index]
        while now < query['time'] - 1e-12:
            active = bisect.bisect_right(times, now + 1e-12) - 1
            control = controls[active]
            end = min(query['time'], now + 0.025,
                      times[active + 1] if active + 1 < len(times) else query['time'])
            mixtures = network.mix(states, control)
            inlets = network.inlets(mixtures)
            for state, flow, inlet in zip(states, control['flows'], inlets):
                state.advance(end - now, flow, inlet)
            now = end
        control = controls[bisect.bisect_right(times, query['time']) - 1]
        snapshots[index] = {'time': query['time'], 'nodes': network.mix(states, control),
                            'probes': [states[p['pipe']].sample(p['position']) for p in query['probes']],
                            'pipe_heat': [state.heat() for state in states]}
    return {'snapshots': snapshots}


def publish(path, result):
    payload = (json.dumps(result, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')) + '\n').encode('utf-8')
    if len(payload) > 2_000_000:
        raise RuntimeError('Output exceeds 2 MB')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=os.path.dirname(os.path.abspath(path)),
                                         prefix='.heat-', suffix='.tmp', delete=False) as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


def main():
    if len(sys.argv) != 3:
        raise ValueError('usage: heat.py INPUT.json OUTPUT.json')
    with open(sys.argv[1], encoding='utf-8') as stream:
        data = json.load(stream)
    publish(sys.argv[2], simulate(data))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('heat: ' + str(error), file=sys.stderr)
        sys.exit(1)
