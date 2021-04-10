#!/usr/local/python3
"""Configuration script for Faulhaber motors."""
import argparse
import logging
import sys
import time

import canopen

if sys.platform == 'darwin':
    from being.can.pcan_darwin_patch import patch_pcan_on_darwin
    patch_pcan_on_darwin()


POSSIBLE_BIT_RATES = [
    1000000, 800000, 500000, 250000, 125000, 100000, 50000, 20000, 10000,
]
"""list: Possible bit / baud rates."""


def cli():
    """Command line interface."""
    parser = argparse.ArgumentParser(description='Being CANopen motor configuration')
    parser.add_argument('nodeId', type=int, help='Desired node id for motor')
    parser.add_argument('bitrate', type=int, help='Desired bit / baud rate',
                        nargs='?', choices=POSSIBLE_BIT_RATES, default=1000000)
    return parser.parse_args()


def bus_params():
    """System dependent bus parameters."""
    if sys.platform == 'darwin':
        return 'pcan', 'PCAN_USBBUS1'

    return 'socketcan', 'can0'


if __name__ == '__main__':
    LOGGER = logging.getLogger('Motor Configurator')
    logging.basicConfig(level=0)
    args = cli()
    network = canopen.Network()

    try:
        bustype, channel = bus_params()
        network.connect(bustype=bustype, channel=channel, bitrate=args.bitrate)

        LOGGER.info('CONFIGURATION_STATE')
        network.lss.send_switch_state_global(network.lss.CONFIGURATION_STATE)

        #LOGGER.info('LSS Scanning')
        #scan = network.lss.fast_scan()
        #print('Result:', scan)

        LOGGER.info('Configuring node')
        network.lss.configure_node_id(args.nodeId)
        idx = POSSIBLE_BIT_RATES.index(args.bitrate)
        network.lss.configure_bit_timing(idx)

        time.sleep(1.)

        #LOGGER.info('inquiring node id')
        #node_id = network.lss.inquire_node_id()
        #LOGGER.info('Node id:', node_id)

        LOGGER.info('Storing configuration')
        network.lss.store_configuration()

        LOGGER.info('WAITING_STATE')
        network.lss.send_switch_state_global(network.lss.WAITING_STATE)

        LOGGER.info('Configuration successful (hopefully?)')

    finally:
        network.disconnect()
