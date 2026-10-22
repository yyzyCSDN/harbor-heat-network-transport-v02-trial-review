"""Candidate-independent public shape, finite value and tolerance checker."""
import math


def verify(data, out, expected):
    errors = []

    def finite(value, path):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f'{path}: non-finite number')
        elif isinstance(value, dict):
            for key, val in value.items():
                finite(val, f'{path}.{key}')
        elif isinstance(value, list):
            for i, val in enumerate(value):
                finite(val, f'{path}[{i}]')

    def number(value, target, tolerance, path):
        if type(value) not in (int, float) or not math.isfinite(value):
            errors.append(f'{path}: expected finite number')
        elif abs(value-target) > tolerance:
            errors.append(f'{path}: error {abs(value-target):.12g} exceeds {tolerance:g}; got {value:.12g}, expected {target:.12g}')

    try:
        finite(out, 'output')
        if not isinstance(out, dict) or not isinstance(out.get('snapshots'), list):
            return errors+['output.snapshots: expected array']
        if len(out['snapshots']) != len(data['queries']):
            return errors+['output.snapshots: wrong length']
        for i, (query, actual, target) in enumerate(zip(data['queries'],out['snapshots'],expected['snapshots'])):
            prefix = f'snapshots[{i}]'
            if not isinstance(actual,dict):
                errors.append(prefix+': expected object')
                continue
            number(actual.get('time'),query['time'],0,prefix+'.time')
            for key, count, tolerance in [('nodes',data['nodes'],5e-5),
                                           ('probes',len(query['probes']),5e-5),
                                           ('pipe_heat',len(data['pipes']),2e-3)]:
                vals=actual.get(key)
                if not isinstance(vals,list) or len(vals)!=count:
                    errors.append(prefix+'.'+key+': wrong array shape')
                    continue
                for j,(value,wanted) in enumerate(zip(vals,target[key])):
                    path=f'{prefix}.{key}[{j}]'
                    if wanted is None:
                        if value is not None:
                            errors.append(path+': expected null')
                    else:
                        number(value,wanted,tolerance,path)
    except (TypeError, ValueError, KeyError, IndexError, OverflowError, RecursionError) as error:
        errors.append('malformed output: '+str(error))
    return errors
