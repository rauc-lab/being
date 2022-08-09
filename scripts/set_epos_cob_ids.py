#!/usr/local/python3

import argparse
import logging
from being.backends import CanBackend
from being.logging import setup_logging, suppress_other_loggers
from being.can.cia_402 import CiA402Node
from being.can import load_object_dictionary
from being.resources import register_resource, manage_resources


def print_cob_ids(node):
    print('RxPDO IDs:', end='\t')
    for i in range(4):
        print(hex(node.rpdo[i+1].cob_id), end='\t')
    print('\nTxPDO IDs:', end='\t')
    for i in range(4):
        print(hex(node.tpdo[i+1].cob_id), end='\t')
    print()


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('nodeId', type=int, help='Target controller ID')
    parser.add_argument('-w', '--write', action='store_true', help='Write COB IDs')
    return parser.parse_args()


def main():
    log_level = logging.INFO
    logging.basicConfig(level=log_level)
    setup_logging(level=log_level)
    suppress_other_loggers()

    args = cli()

    with manage_resources():
        network = CanBackend.single_instance_setdefault()
        register_resource(network)

        node_id = args.nodeId
        object_dictionary = load_object_dictionary(network, node_id)
        node = CiA402Node(node_id, object_dictionary, network)
        print('Current:')
        print_cob_ids(node)

        if args.write:
            settings = {}
            for i in range(4):
                settings[f'Receive PDO {i+1} parameter/COB-ID used by RxPDO {i+1}'] = 0x200 + 0x100 * i + node_id
                settings[f'Transmit PDO {i + 1} parameter/COB-ID used by TxPDO {i + 1}'] = 0x180 + 0x100 * i + node_id
            node.apply_settings(settings)
            node.sdo['Store parameters']['Save all parameters'].data = 'save'.encode()

            node.tpdo.read()
            node.rpdo.read()
            print('New:')
            print_cob_ids(node)


if __name__ == '__main__':
    main()
