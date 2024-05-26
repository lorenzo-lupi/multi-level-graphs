from abc import ABC, abstractmethod
from typing import Callable, Dict, Any, Set, Optional, FrozenSet

from multilevel_graphs.dec_graphs import DecGraph, Supernode, Superedge
from multilevel_graphs.contraction_schemes import DecTable, UpdateQuadruple, ComponentSet


class ContractionScheme(ABC):
    level: int
    dec_graph: Optional[DecGraph]
    contraction_sets_table: Optional[DecTable]
    supernode_table: Dict[FrozenSet[ComponentSet], Supernode]
    update_quadruple: UpdateQuadruple

    _supernode_id_counter: int
    _component_set_id_counter: int
    _supernode_attr_function: Callable[[Supernode], Dict[str, Any]]
    _superedge_attr_function: Callable[[Superedge], Dict[str, Any]]
    _c_set_attr_function: Callable[[Set[Supernode]], Dict[str, Any]]

    def __init__(self,
                 supernode_attr_function: Callable[[Supernode], Dict[str, Any]] = None,
                 superedge_attr_function: Callable[[Superedge], Dict[str, Any]] = None,
                 c_set_attr_function: Callable[[Set[Supernode]], Dict[str, Any]] = None):
        """
        Initializes a contraction scheme based on the contraction function
        defined for this scheme.

        :param supernode_attr_function: a function that returns the attributes to assign to each supernode of this scheme
        :param superedge_attr_function: a function that returns the attributes to assign to each superedge of this scheme
        :param c_set_attr_function: a function that returns the attributes to assign to each component set of this scheme
        """
        self._supernode_id_counter = 0
        self._component_set_id_counter = 0
        self._supernode_attr_function = supernode_attr_function if supernode_attr_function else lambda x: {}
        self._superedge_attr_function = superedge_attr_function if superedge_attr_function else lambda x: {}
        self._c_set_attr_function = c_set_attr_function if c_set_attr_function else lambda x: {}
        self._valid = False
        self.level = 0
        self.dec_graph = None
        self.contraction_sets_table = None
        self.supernode_table = dict()
        self.update_quadruple = UpdateQuadruple()

    @property
    @abstractmethod
    def contraction_name(self) -> str:
        """
        Returns the name of the contraction scheme.
        The name should be unique among all the implementations of the ContractionScheme class.
        The name of the contraction scheme is used as part of the key for each supernode in the
        decontractible graph of this contraction scheme.

        :return: the name of the contraction scheme
        """
        pass

    @abstractmethod
    def clone(self):
        """
        Instantiates and returns a new contraction scheme with the same starting attributes as this one,
        such as attribute functions and others based on the implementation.
        The new contraction scheme does not preserve any information about the contraction sets or the
        decontractible graph of the clones one.

        This method is used internally by the multilevel graph to create new contraction schemes based on their
        construction parameters and preserve their encapsulation.

        :return: a new contraction scheme with the same starting attributes as this one
        """
        pass

    @abstractmethod
    def contraction_function(self, dec_graph: DecGraph) -> DecTable:
        """
        Returns a dictionary of contraction sets for the given decontractible graph
        according to this contraction scheme.

        :param dec_graph: the decontractible graph to be contracted
        """
        pass

    @abstractmethod
    def update_added_node(self, supernode: Supernode):
        """
        Updates the structure of the decontractible graph of this contraction scheme according to the addition
        of the given supernode at the immediate lower level.

        :param supernode: the supernode added to the lower level decontractible graph
        """
        pass

    @abstractmethod
    def update_removed_node(self, supernode: Supernode):
        """
        Updates the structure of the decontractible graph of this contraction scheme according to the removal
        of the given supernode at the immediate lower level.

        :param supernode: the supernode removed from the lower level decontractible graph
        """
        pass

    @abstractmethod
    def update_added_edge(self, superedge: Superedge):
        """
        Updates the structure of the decontractible graph of this contraction scheme according to the addition
        of the given superedge at the immediate lower level.

        :param superedge: the superedge added to the lower level decontractible graph
        """
        pass

    @abstractmethod
    def update_removed_edge(self, superedge: Superedge):
        """
        Updates the structure of the decontractible graph of this contraction scheme according to the removal
        of the given superedge at the immediate lower level.

        :param superedge: the superedge removed from the lower level decontractible graph
        """
        pass

    def update(self, update_quadruple: UpdateQuadruple) -> DecGraph:
        """
        Updates the structure of the decontractible graph of this contraction scheme according to the given
        update quadruple, indicating the changes in the supernodes and superedges of the decontractible graph at
        the immediate lower level.

        :param update_quadruple: the update quadruple indicating the changes in the lower level decontractible graph
        :return: the updated decontractible graph of this contraction scheme
        """
        for edge in update_quadruple.e_minus:
            self.update_removed_edge(edge)
        for node in update_quadruple.v_minus:
            self.update_removed_node(node)
        for node in update_quadruple.v_plus:
            self.update_added_node(node)
        for edge in update_quadruple.e_plus:
            self.update_added_edge(edge)

        return self.dec_graph

    def _get_supernode_id(self) -> int:
        """
        Returns a unique identifier for the supernodes of this contraction scheme.
        Each new identifier is tracked by incrementing the identifier counter.

        :return: a new unique identifier
        """
        self._supernode_id_counter += 1
        return self._supernode_id_counter

    def _get_component_set_id(self) -> int:
        """
        Returns a unique identifier for the component sets of this contraction scheme.
        Each new identifier is tracked by incrementing the identifier counter.

        :return: a new unique identifier
        """
        self._component_set_id_counter += 1
        return self._component_set_id_counter

    def contract(self, dec_graph: DecGraph) -> DecGraph:
        """
        Modifies the state of this contraction scheme constructing a decontractible from the given decontractible
        graph according to this contraction scheme.

        :param dec_graph: the decontractible graph to be contracted
        :return: the contracted decontractible graph
        """
        self.contraction_sets_table = self.contraction_function(dec_graph)
        self.dec_graph = self._make_dec_graph(self.contraction_sets_table, dec_graph)
        self.update_attr()
        self._valid = True
        return self.dec_graph

    def is_valid(self):
        """
        Returns whether the decontractible graph of this contraction scheme is valid, that is, it has been
        contracted and is up-to-date with the changes in the lower level decontractible graph.

        :return: True if the decontractible graph is valid, False otherwise
        """
        return self._valid

    def invalidate(self):
        """
        Marks the decontractible graph of this contraction scheme as invalid, that is, it has not been contracted
        or is not up-to-date with the changes in the lower level decontractible graph.
        """
        self._valid = False

    def _make_dec_graph(self, dec_table: DecTable, dec_graph: DecGraph) -> DecGraph:
        """
        Constructs a decontractible graph from the given decontractible graph
        and the table containing the mapping between nodes and their set of contraction sets.

        :param dec_table: a table of contraction sets
        :param dec_graph: the decontractible graph to be contracted
        """
        self.supernode_table = dict()
        contracted_graph = DecGraph()

        # For each node, we assign it to a supernode corresponding to the set of component sets
        for node, set_of_sets in dec_table:
            f_set_of_sets = frozenset(set_of_sets)
            if f_set_of_sets not in self.supernode_table:
                supernode = \
                    Supernode(key=str(self.level) + "_" + self.contraction_name + "_" + str(self._get_supernode_id()),
                              level=self.level,
                              set_of_sets=f_set_of_sets)

                self.supernode_table[f_set_of_sets] = supernode
                contracted_graph.add_node(supernode)
            else:
                supernode = self.supernode_table[f_set_of_sets]

            supernode.add_node(node)
            node.supernode = supernode

        # For each edge, we assign it to a superedge if the tail and head are in different supernodes,
        # otherwise we assign it to the supernode containing both tail and head.
        for edge in dec_graph.edges():
            tail = edge.tail
            head = edge.head
            if tail.supernode != head.supernode:
                contracted_graph.E.setdefault((tail.supernode.key, head.supernode.key),
                                              Superedge(tail.supernode,
                                                        head.supernode,
                                                        level=self.level)) \
                    .add_edge(edge)
            else:
                tail.supernode.add_edge(edge)

        return contracted_graph

    def update_attr(self):
        """
        Updates the attributes of the supernodes, superedges and component sets of this contraction scheme.
        """
        for supernode in self.dec_graph.nodes():
            supernode.update(**self._supernode_attr_function(supernode))
        for superedge in self.dec_graph.edges():
            superedge.update(**self._superedge_attr_function(superedge))
        for c_set in self.contraction_sets_table.get_all_c_sets():
            c_set.update(**self._c_set_attr_function(set(c_set)))
