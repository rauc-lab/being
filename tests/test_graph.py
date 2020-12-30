import unittest

from being.graph import Graph, find_back_edges, remove_back_edges, topological_sort


class TestGraph(unittest.TestCase):
    def test_graph_has_no_duplicates(self):
        graph = Graph(vertices=[1, 1, 1])

        self.assertEqual(graph.vertices, (1, ))

        edges = 10 * [(1, 2)]
        graph = Graph(edges=edges)

        self.assertEqual(graph.edges, ((1, 2),))
        self.assertEqual(graph.successors, {1: [2]})
        self.assertEqual(graph.predecessors, {2: [1]})

    def test_element_order_equals_initial_order(self):
        vertices = ('a', 'b', 'c')
        edges = ((1, 2), (2, 3), (3, 4))
        graph = Graph(vertices, edges)

        self.assertEqual(graph.vertices, ('a', 'b', 'c', 1, 2, 3, 4))
        self.assertEqual(graph.edges, edges)

    def test_disconnected_graph_has_no_edges(self):
        graph = Graph(vertices=[1, 2, 3])

        self.assertEqual(len(graph.edges), 0)
        self.assertEqual(graph.successors, {})
        self.assertEqual(graph.predecessors, {})

    def test_correct_vertices_from_edges(self):
        edges = ((1, 2), (2, 3), (3, 4))
        graph = Graph(edges=edges)

        self.assertEqual(graph.vertices, (1, 2, 3, 4))

    def test_mutating_raises_attribute_error(self):
        graph = Graph()

        with self.assertRaises(AttributeError):
            graph.vertices = 'something else'

        with self.assertRaises(AttributeError):
            graph.edges = 'something else'

    def test_empty_graph_leads_to_nowhere(self):
        graph = Graph()

        self.assertEqual(len(graph.vertices), 0)
        self.assertEqual(len(graph.edges), 0)
        self.assertEqual(graph.successors, {})
        self.assertEqual(graph.predecessors, {})

    def test_relationship_dicts(self):
        edges = (('a', 'b'), ('b', 'd'), ('a', 'c'), ('c', 'd'), ('d', 'a'))
        graph = Graph(edges=edges)
        self.assertEqual(graph.successors, {
            'a': ['b', 'c'],
            'b': ['d'],
            'c': ['d'],
            'd': ['a'],
        })
        self.assertEqual(graph.predecessors, {
            'a': ['d'],
            'b': ['a'],
            'c': ['a'],
            'd': ['b', 'c'],
        })


class TestBackEdges(unittest.TestCase):
    def test_correct_back_edge_in_test_graph(self):
        edges = (('a', 'b'), ('b', 'd'), ('a', 'c'), ('c', 'd'), ('d', 'a'))
        graph = Graph(edges=edges)
        backEdges = tuple(find_back_edges(graph))

        self.assertEqual(backEdges, (('d', 'a'),))

    def test_forward_edges_are_not_mislabled(self):
        edges = ((1, 2), (2, 3), (1, 3))
        graph = Graph(edges=edges)
        backEdges = list(find_back_edges(graph))

        self.assertEqual(backEdges, [])

    def test_selected_back_edge_in_sync_with_insertion_order(self):
        edges = ((1, 2), (2, 3), (3, 1))
        graph = Graph(edges=edges)
        backEdges = list(find_back_edges(graph))

        self.assertEqual(backEdges, [(3, 1)])

        graph = Graph(edges=reversed(edges))
        backEdges = list(find_back_edges(graph))

        self.assertEqual(backEdges, [(2, 3)])

    def test_removing_back_edges_leads_to_dag(self):
        edges = ((1, 2), (2, 3), (3, 1))
        graph = Graph(edges=edges)
        dag = remove_back_edges(graph)

        self.assertEqual(dag.vertices, (1, 2, 3))
        self.assertEqual(dag.edges, ((1, 2), (2, 3)))


class TopologicalSorting(unittest.TestCase):

    """Test topological_sort with multiple graph examples. Topological sortings
    are not unique.
    """

    def test_sequence_of_three(self):
        edges = [(0, 1), (1, 2)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2])

    def test_simple_back_edge(self):
        edges = [(0, 1), (1, 2), (1, 3), (3, 1)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 3])

    def test_two_branches(self):
        edges = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 3)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 4, 3])

    def test_two_branches_with_bridge(self):
        edges = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 3), (2, 4)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 4, 3])

    def test_two_branches_with_bridge_reverse(self):
        edges = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 3), (4, 2)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 4, 2, 3])

    def test_duo_circle(self):
        edges = [(0, 1), (1, 0)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1])

    def test_double_duo_circle(self):
        edges = [(0, 1), (1, 0), (2, 3), (3, 2)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 3])

    def test_circle_of_three(self):
        edges = [(0, 1), (1, 2), (2, 0)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2])

    def test_raute_with_circle(self):
        edges = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 1), (2, 3)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 3])

    def test_merge_with_back_bridges(self):
        edges = [
            (0, 1), (1, 2), (2, 6),
            (3, 4), (4, 5), (5, 6),
            (2, 4), (5, 1),
        ]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 3, 4, 5, 6])

    def test_sequence_of_four_with_skip(self):
        edges = [
            (0, 1), (1, 2), (2, 3),
            (1, 2)
        ]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 3])

    def test_reverse_sequence_of_five_with_circle_at_the_beginning(self):
        edges = [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (4, 5)]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [4, 3, 2, 1, 0, 5])

    def test_other_graph_from_youtube_video(self):
        edges = [
            (0, 1), (0, 2), (0, 3),
            (1, 2),
            (3, 4),
            (4, 5),
            (5, 3),
        ]
        graph = Graph(edges=edges)
        order = topological_sort(graph)

        self.assertEqual(order, [0, 1, 2, 3, 4, 5])


if __name__ == '__main__':
    unittest.main()
