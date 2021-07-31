"""Helpers for converting choreo motion format to splines.

Choreos are ini files where each motion curve is defined under its own section.
Section name corresponds to motor id. Example:

    [7]
    # format time[s]=pos,vel,acc,dec [all in SI]

    0.175=0.0865, 0.1504, 0.3568, 0.3568
    1.019=0.0329, 0.1037, 0.2006, 0.2006
    2.053=0.0969, 0.1498, 0.3502, 0.3502
    2.908=0.0270, 0.1048, 0.1569, 0.1569

    [8]
    # format time[s]=pos,vel,acc,dec [all in SI]

    0.870=0.0904, 0.1277, 0.2495, 0.2495
    1.894=0.0315, 0.0847, 0.1219, 0.1219
    3.283=0.0806, 0.1286, 0.3372, 0.3372
"""
import warnings
from typing import Iterable, List, Generator
from configparser import ConfigParser, SectionProxy

import numpy as np
from scipy.interpolate import PPoly

from being.kinematics import State
from being.spline import optimal_trajectory_spline, copy_spline, ppoly_insert


Choreo = ConfigParser
Segment = List
Segments = Generator[Segment, None, None]


def collect_segments_from_section(section) -> Segments:
    """Collect motion segments from section."""
    for when, what in section.items():
        t = float(when)
        pos, maxVel, maxAcc, maxDec = map(float, what.split(','))
        if maxAcc != maxDec:
            warnings.warn('Deviating maximum acc-/ deceleration are not supported')

        yield t, pos, maxVel, maxAcc


def collect_segments_from_choreo(choreo: Choreo):
    """Collect motion segments for each motion channel from choreo."""
    for name in choreo.sections():  # Skips DEFAULT section
        section = choreo[name]
        yield collect_segments_from_section(section)


def convert_segments_to_spline(segments, start=State()) -> Generator[PPoly, None, None]:
    """Convert motion segments to multiple disjoint optimal trajectory splines.
    Each optimal trajectory splines represents a choreo segment (best
    effort). They can overlap but do not have to.
    """
    prevSpline = None
    for t, pos, maxSpeed, maxAcc in segments:
        end = State(pos)
        if prevSpline:
            start = State(position=prevSpline(t), velocity=prevSpline(t, nu=1))

        spline = optimal_trajectory_spline(start, end, maxSpeed, maxAcc, extrapolate=True)
        spline.x += t

        yield spline

        prevSpline = spline


def combine_splines_in_time(splines: Iterable[PPoly]) -> PPoly:
    """Combine multiple one dimensional splines in time. Takes care of overlap
    situation. Assumes that input splines can be extrapolated.
    """
    splines = iter(splines)
    spline = copy_spline(next(splines))
    for s in splines:
        overlap = spline.x[-1] - s.x[0]
        if overlap < 0:
            spline = ppoly_insert(s.x[0], spline)
        elif overlap > 0:
            spline.x[-1] -= overlap

        spline.extend(s.c, s.x[1:])

    return spline


def combine_splines_in_dimensions(splines):
    """Pack / stack mutiple single dimensional splines into one. Inserts missing
    knots if the single dimensional splines do not align up.
    """
    splines = [copy_spline(s) for s in splines]
    allXs = np.concatenate([s.x for s in splines])
    unique = np.unique(allXs)
    unique.sort()

    for i in range(len(splines)):
        for x in unique:
            if x not in splines[i].x:
                splines[i].extrapolate = False
                splines[i] = ppoly_insert(x, splines[i])

    c = np.dstack([s.c for s in splines])
    return PPoly.construct_fast(
        c,
        unique,
        extrapolate=False,
        axis=0
    )


def convert_choreo_to_spline(choreo: Choreo) -> PPoly:
    """Convert choreo to spline."""
    segmentsPerChannel = collect_segments_from_choreo(choreo)
    splines = map(convert_segments_to_spline, segmentsPerChannel)
    channels = map(combine_splines_in_time, splines)
    return combine_splines_in_dimensions(channels)
