"""Execution of blocks."""
import collections

from typing import Iterable, List

from being.block import Block, output_neighbors, input_neighbors
from being.graph import Graph, topological_sort


ExecOrder = List[Block]
"""List of topological sorted blocks."""


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

    return Graph(vertices, edges)


def determine_execution_order(blocks: Iterable[Block]) -> ExecOrder:
    """Determine execution order for blocks."""
    graph = block_network_graph(blocks)
    return topological_sort(graph)


def execute(execOrder: ExecOrder):
    """Execute execution order."""
    for block in execOrder:
        block.update()
