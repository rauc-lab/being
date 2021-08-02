#!/bin/python3
"""Convert choreo files to BPoly splines CLI util."""
import argparse
import configparser
import glob
import json
import os

from scipy.interpolate import BPoly

from being.choreo import convert_choreo_to_spline
from being.serialization import dumps, BeingEncoder
from being.utils import rootname


def cli(args=None):
    parser = argparse.ArgumentParser(description='Choreo converter.')
    parser.add_argument('choreos', type=str, nargs='+', help='choreo file to convert')
    parser.add_argument('-o', '--outputDir', type=str, default=None, help='output directory')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='Verbose console output')
    return parser.parse_args(args)


def collect_choreo_files(filepaths):
    for fp in filepaths:
        if '*' in fp:
            yield from glob.glob(fp)
        elif os.path.isdir(fp):
            search = os.path.join(fp, '*.choreo')
            yield from glob.glob(search)
        else:
            yield fp


def unique_elements(iterable):
    seen = set()
    for ele in iterable:
        if ele in seen:
            continue

        seen.add(ele)
        yield ele


def main():
    args = cli()
    choreos = list(collect_choreo_files(args.choreos))
    choreos = list(unique_elements(choreos))
    if args.outputDir:
        if not os.path.isdir(args.output):
            raise ValueError('Output directory has to be a directory!')

    for src in choreos:
        print('Converting:', src)

        if args.verbose: print('  Opening .ini file')
        choreo = configparser.ConfigParser()
        with open(src) as f:
            choreo.read_file(f)

        if args.verbose: print('  Converting choreo to BPoly spline')
        ppoly = convert_choreo_to_spline(choreo)
        motion = BPoly.from_power_basis(ppoly)

        if args.verbose: print('  Serializing spline')
        s = dumps(motion)

        if args.verbose: print('  Saving spline')
        if args.outputDir is None:
            head, tail = os.path.split(src)
            dst = os.path.join(head, rootname(tail) + '.json')
        else:
            dst = os.path.join(head, rootname(tail) + '.json')

        with open(dst, 'w') as fp:
            json.dump(motion, fp, cls=BeingEncoder)
            print(f'Saved motion to {dst!r}')


if __name__ == '__main__':
    main()
