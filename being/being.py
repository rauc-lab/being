"""Awaking a being to live. Main start execution entry point."""
import collections
import time

from typing import Iterable, List

from being.backends import CanBackend
from being.block import Block, output_neighbors, input_neighbors
from being.graph import Graph, topological_sort
from being.motor import home_motors, Motor
from being.config import INTERVAL
from being.resources import add_callback


def block_network_graph(blocks: Iterable[Block]) -> Graph:
    """Traverse block network and build block network graph.

    Args:
        blocks (iterable): Starting blocks for graph traversal.

    Returns:
        Block network graph.
    """
    vertices = []
    edges = set()
    queue = collections.deque(blocks)
    while queue:
        block = queue.popleft()
        if block not in vertices:
            vertices.append(block)
            for successor in output_neighbors(block):
                edges.add((block, successor))
                queue.append(successor)

            for predecessor in input_neighbors(block):
                edges.add((predecessor, block))
                queue.append(predecessor)

    return Graph(vertices=vertices, edges=edges)


def find_all_motors(execOrder) -> List[Motor]:
    """Find all motor blocks in execOrder."""
    return [
        b for b in execOrder
        if isinstance(b, Motor)
    ]


def awake(*blocks, web=False):
    """Run being."""
    being = Being(blocks)
    if not web:
        being.run()

    else:
        # TODO: Init web server
        pass


class Being:

    """Being core."""

    def __init__(self, blocks):
        graph = block_network_graph(blocks)
        self.execOrder = topological_sort(graph)
        # TODO: Validate execOrder
        self.network = None
        if CanBackend.initialized():
            self.network = CanBackend.default()

        motors = find_all_motors(self.execOrder)
        if motors:
            home_motors(motors)
            self.network.enable_drives()
            add_callback(self.network.disable_drives)

    def run(self):
        while True:
            t0 = time.perf_counter()
            for block in self.execOrder:
                block.update()

            if self.network is not None:
                self.network.send_sync()

            t1 = time.perf_counter()
            time.sleep(max(0, INTERVAL - (t1 - t0)))

    async def async_run(self):
        pass
