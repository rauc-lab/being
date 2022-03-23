#!/usr/local/python3
import warnings
warnings.filterwarnings("ignore", category=UserWarning,
                                   module="being.backends")

from being.backends import CanBackend
from being.resources import register_resource, manage_resources


with manage_resources():
    network = CanBackend.single_instance_setdefault()
    register_resource(network, duplicates=False)
    nodeIds = network.scan_for_node_ids()
    print(nodeIds)
