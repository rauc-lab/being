"""Graphing and topological sorting."""
import collections
import itertools
from typing import ForwardRef, Generator, Hashable, Iterable, List, Optional, Sequence, Tuple


Vertex = Hashable
"""Graph vertex."""

Edge = Tuple[Vertex, Vertex]
"""Source -> destination graph edge."""

Graph = ForwardRef('Graph')


def unique_elements(iterable: Iterable[Hashable]) -> Generator[Hashable, None, None]:
    """Iterate over unique elements in iterable."""
    seen = set()
    for element in itertools.filterfalse(seen.__contains__, iterable):
        seen.add(element)
        yield element


def find_back_edges(graph) -> Generator[Edge, None, None]:
    """Find back edges of graph.

    Args:
        graph: Input graph.

    Yields:
        Source to destination back edges.

    See Also:
        `Output of a depth-first search <https://en.wikipedia.org/wiki/Depth-first_search#Output_of_a_depth-first_search>`_
    """
    paths = collections.deque([v] for v in graph.vertices)
    visited = set()
    while paths:
        path = paths.popleft()
        src = path[-1]
        if src in visited:
            continue

        visited.add(src)
        for dst in reversed(graph.successors[src]):
            if dst in path:
                yield src, dst
            else:
                paths.appendleft(path + [dst])


def remove_back_edges(graph: Graph) -> Graph:
    """Remove back edges from graph an return new DAG.

    Args:
        graph: Input graph.

    Returns:
        DAG
    """
    backEdges = list(find_back_edges(graph))
    if not backEdges:
        return graph

    edges = list(graph.edges)
    for backEdge in backEdges:
        edges.remove(backEdge)

    noBackEdges = edges
    return Graph(graph.vertices, edges=noBackEdges)


def topological_sort(graph: Graph) -> List[Vertex]:
    """Topological sorting of directed graph vertices.

    Args:
        Input graph.

    Returns:
        Topological sorting.
    """
    order = []
    dag = remove_back_edges(graph)

    def vertex_is_ready(vertex: Vertex) -> bool:
        """Check if vertex is ready for insertion into topological order."""
        return all(p in order for p in dag.predecessors[vertex])

    queue = collections.deque(dag.vertices)
    while queue:
        vertex = queue.popleft()
        if vertex in order:
            continue

        successors = reversed(dag.successors[vertex])
        if vertex_is_ready(vertex):
            order.append(vertex)
            queue.extendleft(successors)
        else:
            queue.extend(successors)

    return order


class Graph(collections.namedtuple('Graph', ['vertices', 'edges', 'successors', 'predecessors'])):

    """Immutable graph. Graph vertices can be any hashable Python object. An
    edge is a source -> destination tuple. A graph is a tuple of a vertex and a
    edges sets.

    Note:
        Tuples instead of sets to preserve order.

    Attributes:
        vertices (tuple): Graph vertices.
        edges (tuple): Graph edges.
        successors (collections.defaultdict): Source -> destinations
            relationships. For each source vertex get a list of destination
            vertices.
        predecessors (collections.defaultdict): Destination -> sources
            relationships. For each destination vertex get a list of source
            vertices.
    """

    # __slots__ = ()  # ...consenting adults

    def __new__(cls, vertices: Optional[Iterable] = None,
            edges: Sequence[Edge] = None):
        """
        Args:
            vertices: Initial vertices. Final vertices will be auto updated from
                the ones present in the edges.
            edges: Source -> destination edge tuples.
        """
        vertices = list(vertices or [])
        edges = list(edges or [])
        for edge in edges:
            vertices.extend(edge)

        vertices = tuple(unique_elements(vertices))
        edges = tuple(unique_elements(edges))

        successors = collections.defaultdict(list)
        predecessors = collections.defaultdict(list)
        for src, dst in edges:
            successors[src].append(dst)
            predecessors[dst].append(src)

        return super().__new__(cls, vertices, edges, successors, predecessors)

    def __str__(self):
        return '%s(%d vertices, %d edges)' % (
            type(self).__name__,
            len(self.vertices),
            len(self.edges),
        )
