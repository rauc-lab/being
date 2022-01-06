"""Block execution. Given some interconnected blocks find a suitable *order* to
execute them in. Aka. calling the :meth:`being.block.Block.update` methods in an
appropriate order.

Caution:
    If the block network graph has cycles it is not possible to resolve a
    *proper* execution order. In this case blocks will have to work with out of
    date data.

    .. digraph:: cycle
        :align: center
        :alt: Directed graph with cycle
        :caption: Directed graph with cycle
        :name: Directed graph with cycle

        node [shape=box];
        bgcolor="#ffffff00"
        a -> b -> c;
        b -> d;
        d -> b;
        {rank = same; a; b; c;}

    This graph has a cycle between *b* and *d* and the resulting execution order
    is *[a, b, c, d]* (*c* and *d* could be swapped depending on the insertion
    order).
"""
import collections

from typing import Iterable, List

from being.block import Block, output_neighbors, input_neighbors
from being.graph import Graph, topological_sort


ExecOrder = List[Block]
"""List of topological sorted blocks."""


def block_network_graph(blocks: Iterable[Block]) -> Graph:
    """Traverse block network and build block network graph.

    Args:
        blocks: Starting blocks for graph traversal.

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
    """Determine execution order for blocks.

    Args:
        blocks: Interconnected blocks.

    Returns:
        Execution order.
    """
    graph = block_network_graph(blocks)
    return topological_sort(graph)


def execute(execOrder: ExecOrder):
    """Execute execution order.

    Args:
        execOrder: Blocks to execute.
    """
    for block in execOrder:
        block.update()
