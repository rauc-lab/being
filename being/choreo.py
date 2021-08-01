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
    """Collect motion segments from section.

    Args:
        section: ConfigParser section representing a single motion curve.

    Yields:
        Motion segments.
    """
    for when, what in section.items():
        t = float(when)
        pos, maxVel, maxAcc, maxDec = map(float, what.split(','))
        if maxAcc != maxDec:
            warnings.warn('Deviating maximum acc-/ deceleration are not supported')

        yield t, pos, maxVel, maxAcc


def collect_segments_from_choreo(choreo: Choreo) -> Generator[Segments, None, None]:
    """Collect motion segments for each motion channel from choreo.

    Args:
        Choreo ConfigParser intance

    Yields:
        Segments generator for each motion channel.
    """
    for name in choreo.sections():  # Skips DEFAULT section
        section = choreo[name]
        yield collect_segments_from_section(section)


def convert_segments_to_splines(segments, start=State()) -> Generator[PPoly, None, None]:
    """Convert motion segments to multiple disjoint optimal trajectory splines.
    Each optimal trajectory splines represents a choreo segment (best
    effort). They can overlap but do not have to.

    Args:
        segments: Motion segments. Each row with [time, targetPosition,
            maxSpeed, maxAcceleration].

    Yield:
        Optimal trajectory spline for each segment.
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
        overlap = spline.x[-1] - s.x[0]  # Overlap to previous spline. overlap < 0 -> No overlap
        if overlap < 0:
            spline = ppoly_insert(s.x[0], spline)  # Append knot
        elif overlap > 0:
            spline.x[-1] -= overlap

        spline.extend(s.c, s.x[1:])

    return spline


def _ppoly_insert_inplace(newX, spline, extrapolate):
    """In-place PPoly insert function. Doc: See original ppoly_insert()."""
    new = ppoly_insert(newX, spline, extrapolate)
    spline.x = new.x
    spline.c = new.c


def combine_splines_in_dimensions(splines):
    """Pack / stack multiple single dimensional splines into one. Inserts
    missing knots if the single dimensional splines do not align up.
    """
    splines = [copy_spline(s) for s in splines]
    allKnots = np.concatenate([s.x for s in splines])
    uniqueKnots = np.unique(allKnots)
    uniqueKnots.sort()

    # Add missing knots for each spline
    for spline in splines:
        for knot in uniqueKnots:
            if knot not in spline.x:
                _ppoly_insert_inplace(knot, spline, extrapolate=False)

    coeffs = np.dstack([s.c for s in splines])
    return PPoly.construct_fast(
        coeffs,
        uniqueKnots,
        extrapolate=False,
        axis=0
    )


def convert_choreo_to_spline(choreo: Choreo) -> PPoly:
    """Convert choreo to spline. If there are multiple motion curves defined in
    choreo return multi dimensional spline.

    Args:
        choreo: Configparser for chore file.

    Returns:
        Extracted simulated motion curves.
    """
    segments = collect_segments_from_choreo(choreo)
    splines = map(convert_segments_to_splines, segments)
    curves = map(combine_splines_in_time, splines)
    spline = combine_splines_in_dimensions(curves)
    #return BPoly.from_power_basis(spline)
    return spline
