from rdflib.graph import ConjunctiveGraph, Graph

class IsomorphicGraph(ConjunctiveGraph):
    pass

def to_isomorphic(graph: Graph = ...) -> IsomorphicGraph: ...
