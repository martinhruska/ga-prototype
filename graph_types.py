#! /usr/bin/python3

"""
Basic definitions of data types for graph automata
"""
import collections

Edge = collections.namedtuple('Edge', ['parent', 'symbol', 'children'])
Trans = collections.namedtuple(
    'Transition', ['parent', 'symbol', 'children', 'vars', 'forget', 'jumps'])
Labelling = collections.namedtuple('Labelling', ['state', 'vars', 'forget', 'jumps'])


class Graph:
    def __init__(self):
        self._nodes = set()
        self._edges = []

    def add_edge(self, parent, label, children):
        self._nodes.add(parent)
        self._nodes.union(set(children))
        self._edges.append(Edge(parent, label, children))

    def add_node(self, node):
        self._nodes.add(node)

    @property
    def edges(self):
        return self._edges

    @property
    def nodes(self):
        return self._nodes

    def root(self):
        for node in self._nodes:
            if all([node not in edge.children for edge in self._edges]):
                return node

        raise RuntimeError("No root found ", self._nodes)

    def __iter__(self):
        return self._edges.__iter__()

    def __str__(self):
        res = "Nodes: " + str(self._nodes)
        res += "Edges: " + str(self._edges)

        return res


class GraphAutomaton:
    def __init__(self):
        self._transitions = []

    def __str__(self):
        res = "States: " + str(set([trans.parent for trans in self._transitions]).union(
            [c for trans in self._transitions for c in trans.children]))
        res += "Symbols: " + str(set([s for (_, s, _) in self._transitions]))
        res += "Transition: " + str(self._transitions)

        return res

    def __iter__(self):
        return self._transitions.__iter__()

    @property
    def transitions(self):
        return self._transitions

    def add_create_transition(self, transition):
        self._transitions.append(transition)

    def add_transition(self, parent, symbol, children, variables, forget, jumps):
        self._transitions.append(Trans(parent, symbol, children, variables, forget, jumps))


class Run:
    def __init__(self):
        self._mapping = {}

    def __getitem__(self, node):
        return self._mapping[node]

    def __contains__(self, item):
        return item in self._mapping

    def __iter__(self):
        return self._mapping.__iter__()

    def __str__(self):
        res = ""
        for node in self._mapping.keys():
            res += node + " -> " + str(self._mapping[node]) + '\n'

        return res

    def at(self, node):
        return self._mapping[node]

    def map(self, node, state, variables, forgot, jump):
        if node in self._mapping.keys():
            raise RuntimeError("This node has been already mapped")

        self._mapping[node] = Labelling(state, variables, forgot, jump)

    def get_state(self, node):
        if node not in self._mapping:
            raise RuntimeError("This nodes has not been mapped")

        return self._mapping[node].state
