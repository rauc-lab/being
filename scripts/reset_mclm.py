#!/usr/local/python3

import argparse
import logging
from being.logging import setup_logging, suppress_other_loggers
from being.motors import LinearMotor
from being.resources import manage_resources
from being.can.cia_402 import Command


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('nodeId', type=int, help='Desired node id for motor')
    parser.add_argument('-r', '--reset', action='store_true',
                        help='Reset node')
    return parser.parse_args()


log_level = logging.INFO
logging.basicConfig(level=log_level)
setup_logging(level=log_level)
suppress_other_loggers()


with manage_resources():
    args = cli()
    m = LinearMotor(args.nodeId)
    node = m.controller.node
    node.sdo['Controlword'].raw = Command.DISABLE_VOLTAGE
    if args.reset:
        node.sdo['Restore Default Parameters']['Restore Factory Application Parameters'].data = 'load'.encode()
        node.sdo['Store Parameters']['Save all Parameters'].data = 'save'.encode()
