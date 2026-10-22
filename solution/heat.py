#!/usr/bin/env python3
"""Forward, event-driven transport of spatial exponential temperature profiles."""

from dataclasses import dataclass
from fractions import Fraction
import json
import math
import os
import sys
import tempfile

import numpy as np


def rational(value):
    return Fraction(str(value))


def expression(terms):
    combined = {}
    for rate, coefficient in terms:
        # Slopes arise from additions and divisions of the same loss rates.
        # Canonical keys prevent insignificant arithmetic differences from
        # multiplying an otherwise identical exponential term.
        key = round(float(rate), 14)
        combined[key] = combined.get(key, 0.0) + float(coefficient)
    items = sorted((rate, coefficient) for rate, coefficient in combined.items() if coefficient != 0)
    if not items:
        items = [(0.0, 0.0)]
    return np.array([item[0] for item in items]), np.array([item[1] for item in items])


@dataclass
class Segment:
    left: Fraction
    right: Fraction
    rates: np.ndarray
    coefficients: np.ndarray

    def values(self, position):
        return self.coefficients * np.exp(self.rates * float(position - self.left))

    def temperature_excess(self, position):
        return float(np.sum(self.values(position)))

    def integral(self):
        width = float(self.right - self.left)
        z = self.rates * width
        factor = np.ones_like(z)
        nonzero = z != 0
        factor[nonzero] = np.expm1(z[nonzero]) / z[nonzero]
        return float(width * np.dot(self.coefficients, factor))


def coalesce(segments):
    result = []
    for current in segments:
        if current.left >= current.right:
            continue
        if result:
            previous = result[-1]
            if (previous.right == current.left
                    and np.array_equal(previous.rates, current.rates)):
                at_join = previous.values(current.left)
                # Bound the error term by term over the entire added interval;
                # exponentials reach their absolute maximum at an endpoint.
                width = float(current.right - current.left)
                amplification = np.exp(np.maximum(0.0, current.rates * width))
                discrepancy = float(np.sum(np.abs(at_join - current.coefficients) * amplification))
                if discrepancy <= 2e-12:
                    previous.right = current.right
                    continue
        result.append(current)
    return result


class Transport:
    def __init__(self, data):
        self.data = data
        self.ambient = float(data["ambient"])
        self.volumes = [rational(pipe["volume"]) for pipe in data["pipes"]]
        self.profiles = []
        for pipe in data["pipes"]:
            profile, left = [], Fraction(0)
            for initial in pipe["initial"]:
                right = left + rational(initial["volume"])
                rates, coefficients = expression([(0, initial["temperature"] - self.ambient)])
                profile.append(Segment(left, right, rates, coefficients))
                left = right
            self.profiles.append(coalesce(profile))
        self.time = Fraction(0)
        self.control_index = 0
        self.control_times = [rational(control["time"]) for control in data["controls"]]
        self.steps = 0
        self.maximum_segments = sum(map(len, self.profiles))
        self.maximum_terms = self.term_count()

    def term_count(self):
        return sum(len(segment.rates) for profile in self.profiles for segment in profile)

    @property
    def control(self):
        return self.data["controls"][self.control_index]

    def select_control(self):
        while (self.control_index + 1 < len(self.control_times)
               and self.control_times[self.control_index + 1] <= self.time):
            self.control_index += 1

    def node_functions(self):
        terms = [[] for _ in range(self.data["nodes"])]
        incoming = [0.0] * self.data["nodes"]
        for index, pipe in enumerate(self.data["pipes"]):
            flow = self.control["flows"][index]
            if flow == 0:
                continue
            if flow > 0:
                segment, endpoint, node = self.profiles[index][-1], self.volumes[index], pipe["b"]
            else:
                segment, endpoint, node = self.profiles[index][0], Fraction(0), pipe["a"]
            coefficients = segment.values(endpoint)
            rates = -segment.rates * flow - pipe["loss"]
            amount = abs(flow)
            terms[node].extend(zip(rates, coefficients * amount))
            incoming[node] += amount
        for node, injection in enumerate(self.control["injection"]):
            amount = injection["rate"]
            if amount:
                terms[node].append((0.0, amount * (injection["temperature"] - self.ambient)))
                incoming[node] += amount
        functions = []
        for node in range(self.data["nodes"]):
            if incoming[node] == 0:
                functions.append(None)
            else:
                rates, coefficients = expression(terms[node])
                functions.append((rates, coefficients / incoming[node]))
        return functions

    def advance(self, target):
        while self.time < target:
            self.select_control()
            duration = target - self.time
            if self.control_index + 1 < len(self.control_times):
                duration = min(duration, self.control_times[self.control_index + 1] - self.time)
            for index, flow in enumerate(self.control["flows"]):
                if flow > 0:
                    available = (self.volumes[index] - self.profiles[index][-1].left) / flow
                    duration = min(duration, available)
                elif flow < 0:
                    available = self.profiles[index][0].right / -flow
                    duration = min(duration, available)
            if duration <= 0:
                raise RuntimeError("Nonpositive transport event interval")
            functions = self.node_functions()
            for index, pipe in enumerate(self.data["pipes"]):
                flow = self.control["flows"][index]
                shift = flow * duration
                volume, loss = self.volumes[index], pipe["loss"]
                moved = []
                for segment in self.profiles[index]:
                    left = max(Fraction(0), segment.left + shift)
                    right = min(volume, segment.right + shift)
                    if left < right:
                        coefficients = segment.values(left - shift) * math.exp(-loss * float(duration))
                        moved.append(Segment(left, right, segment.rates, coefficients))
                if flow:
                    node = pipe["a"] if flow > 0 else pipe["b"]
                    if functions[node] is None:
                        raise RuntimeError("Flowing inlet has no upstream water")
                    temporal_rates, coefficients = functions[node]
                    spatial_rates = -(temporal_rates + loss) / flow
                    if flow > 0:
                        left, right = Fraction(0), shift
                        coefficients = coefficients * np.exp(temporal_rates * float(duration))
                    else:
                        left, right = volume + shift, volume
                        coefficients = coefficients * math.exp(-loss * float(duration))
                    rates, coefficients = expression(zip(spatial_rates, coefficients))
                    added = Segment(left, right, rates, coefficients)
                    if flow > 0:
                        moved.insert(0, added)
                    else:
                        moved.append(added)
                self.profiles[index] = coalesce(moved)
                if (not self.profiles[index] or self.profiles[index][0].left != 0
                        or self.profiles[index][-1].right != volume
                        or any(a.right != b.left for a, b in zip(self.profiles[index], self.profiles[index][1:]))):
                    raise RuntimeError("Spatial profile lost coverage")
            self.time += duration
            self.steps += 1
            self.maximum_segments = max(self.maximum_segments, sum(map(len, self.profiles)))
            self.maximum_terms = max(self.maximum_terms, self.term_count())
        self.select_control()

    def probe(self, index, position, node_temperatures):
        flow = self.control["flows"][index]
        pipe, volume = self.data["pipes"][index], self.volumes[index]
        if flow > 0 and position == 0:
            return node_temperatures[pipe["a"]]
        if flow < 0 and position == volume:
            return node_temperatures[pipe["b"]]
        if flow > 0:
            for segment in self.profiles[index]:
                if segment.left < position <= segment.right:
                    return self.ambient + segment.temperature_excess(position)
        else:
            for segment in self.profiles[index]:
                if segment.left <= position < segment.right:
                    return self.ambient + segment.temperature_excess(position)
            if position == volume:
                return self.ambient + self.profiles[index][-1].temperature_excess(position)
        raise RuntimeError("Probe not covered by the spatial profile")

    def snapshot(self, query):
        functions = self.node_functions()
        temperatures = [None if function is None else self.ambient + float(np.sum(function[1]))
                        for function in functions]
        return {"time": query["time"], "nodes": temperatures,
                "probes": [self.probe(probe["pipe"], rational(probe["position"]), temperatures)
                           for probe in query["probes"]],
                "pipe_heat": [4.18 * math.fsum(segment.integral() for segment in profile)
                              for profile in self.profiles]}

    def run(self):
        snapshots = [None] * len(self.data["queries"])
        for index in sorted(range(len(snapshots)), key=lambda index: self.data["queries"][index]["time"]):
            query = self.data["queries"][index]
            self.advance(rational(query["time"]))
            snapshots[index] = self.snapshot(query)
        return {"snapshots": snapshots}


def solve(data):
    return Transport(data).run()


def write_atomic(path, result):
    payload = (json.dumps(result, allow_nan=False, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > 2_000_000:
        raise RuntimeError("Output exceeds size limit")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=os.path.dirname(os.path.abspath(path)),
                                         prefix=".heat-", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def main():
    if len(sys.argv) != 3:
        raise ValueError("usage: heat.py INPUT.json OUTPUT.json")
    with open(sys.argv[1], "r", encoding="utf-8") as stream:
        data = json.load(stream)
    write_atomic(sys.argv[2], solve(data))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("heat: " + str(error), file=sys.stderr)
        sys.exit(1)
