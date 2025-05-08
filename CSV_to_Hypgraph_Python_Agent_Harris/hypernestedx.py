from typing import Dict, List, Set, Union, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import defaultdict, Counter
from heapq import heappop, heappush
from itertools import product
import pandas as pd
import numpy as np
import json
import re
import os

# ===== Base Node Classes ===== #

@dataclass
class BaseNode:
    """Base class for all node types in the heterogeneous network"""
    node_id: str
    node_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    feature_vector: Optional[np.ndarray] = None
    
    def compute_features(self, feature_keys: List[str] = None):
        """Compute a feature vector based on attributes and metadata."""
        if feature_keys:
            features = [self.attributes.get(k, 0) for k in feature_keys]
        else:
            features = list(self.attributes.values())
        self.feature_vector = np.array(features, dtype=float)

    def __post_init__(self):
        self.attributes = {k.lower(): v for k, v in self.attributes.items()}

@dataclass
class TableNode(BaseNode):
    """Node containing tabular data (e.g., relational tables)"""
    data: Union[pd.DataFrame, Dict[str, Any]] = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert internal data to DataFrame"""
        if isinstance(self.data, pd.DataFrame):
            return self.data
        return pd.DataFrame.from_dict(self.data)


@dataclass
class JSONNode(BaseNode):
    """Node containing JSON data with nested structure support"""
    data: Dict[str, Any] = field(default_factory=dict)

    def get_nested_values(self, key_path: str) -> List[Any]:
        """Extract values from nested JSON using dot notation"""
        def get_value(obj: Any, key: str) -> Any:
            if isinstance(obj, dict):
                return obj.get(key)
            elif isinstance(obj, list):
                try:
                    index = int(key)
                    return obj[index] if 0 <= index < len(obj) else None
                except ValueError:
                    return [item.get(key) if isinstance(item, dict) else None for item in obj]
            return None

        current = self.data
        for key in key_path.split('.'):
            if current is None:
                return []
            current = get_value(current, key)

        return [current] if not isinstance(current, list) else current

# ===== Base Edge Classes ===== #

@dataclass
class BaseEdge:
    """
    A base edge in a standard graph (non-hyperedge).
    source_id: The ID of the source node (for directed or undirected).
    target_id: The ID of the target node.
    metadata: Stores arbitrary attributes, including scores.
    """
    edge_id: str
    source_id: str
    target_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_score(self, score_type: str, default: float = 1.0) -> float:
        """
        Utility method to retrieve a particular score from metadata.
        Example: get_score("weight") -> returns metadata["scores"]["weight"] if present.
        """
        scores = self.metadata.get("scores", {})
        return scores.get(score_type, default)

# ===== Hyperedge Classes ===== #

class HyperedgeBase:
    """Base class for all hyperedge types"""
    def __init__(self, edge_id: str, edge_type: str, modality: str, weight: float = 1.0):
        self.edge_id = edge_id
        self.edge_type = edge_type
        self.modality = modality
        self.weight = weight  # can remain for backward-compatibility
        self.feature_vector: Optional[np.ndarray] = None
        
        # We introduce a metadata dict if it does not already exist
        self.metadata: Dict[str, Any] = {}
        # Example: self.metadata["node_scores"] = {node_id: { "weight": ..., "confidence": ... }, ...}

    def compute_features(self, connected_nodes: List[BaseNode]):
        """Compute a feature vector based on connected nodes."""
        node_features = np.array([node.feature_vector for node in connected_nodes if node.feature_vector is not None])
        self.feature_vector = node_features.mean(axis=0) if len(node_features) > 0 else np.zeros(1)


class SimpleHyperedge(HyperedgeBase):
    """Simple hyperedge connecting multiple nodes"""
    def __init__(self, edge_id: str, nodes: List[str], modality: str, weight: float = 1.0, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(edge_id, "simple", modality, weight)
        self.nodes = nodes
        self.metadata = metadata or {}  # hold arbitrary data, including "node_scores"

        # If we want per-node scores, we could store them like this:
        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}  # {node_id: {"weight":..., "confidence":..., ...}}

    def set_node_score(self, node_id: str, score_type: str, value: float):
        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}
        if node_id not in self.metadata["node_scores"]:
            self.metadata["node_scores"][node_id] = {}
        self.metadata["node_scores"][node_id][score_type] = value

    def get_node_score(self, node_id: str, score_type: str, default: float = 1.0) -> float:
        return self.metadata.get("node_scores", {}).get(node_id, {}).get(score_type, default)
    
    def set_pair_score(self, node_a: str, node_b: str, score_type: str, value: float, directed: bool = False):
        if "pair_scores" not in self.metadata:
            self.metadata["pair_scores"] = {}

        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        if pair_key not in self.metadata["pair_scores"]:
            self.metadata["pair_scores"][pair_key] = {}
        self.metadata["pair_scores"][pair_key][score_type] = value

    def get_pair_score(self, node_a: str, node_b: str, score_type: str, default: float = 0.0, directed: bool = False) -> float:
        pair_scores = self.metadata.get("pair_scores", {})
        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        return pair_scores.get(pair_key, {}).get(score_type, default)

    def __and__(self, other: 'SimpleHyperedge') -> 'SimpleHyperedge':
        """Intersection of two simple hyperedges"""
        common_nodes = list(set(self.nodes) & set(other.nodes))
        return SimpleHyperedge(
            f"{self.edge_id}_intersect_{other.edge_id}", common_nodes, f"{self.modality}_{other.modality}"
        )

    def __add__(self, other: 'SimpleHyperedge') -> 'SimpleHyperedge':
        """Union of two simple hyperedges"""
        all_nodes = list(set(self.nodes) | set(other.nodes))
        return SimpleHyperedge(
            f"{self.edge_id}_union_{other.edge_id}", all_nodes, f"{self.modality}_{other.modality}"
        )
    
    def compute_features(self, node_dict: Dict[str, BaseNode]):
        connected_nodes = [node_dict[node_id] for node_id in self.nodes if node_id in node_dict]
        super().compute_features(connected_nodes)


class DirectedHyperedge(HyperedgeBase):
    """Directed hyperedge with source and target nodes"""
    def __init__(
        self,
        edge_id: str,
        source_nodes: List[str],
        target_nodes: List[str],
        modality: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(edge_id, "directed", modality, weight)
        self.source_nodes = source_nodes
        self.target_nodes = target_nodes
        self.metadata = metadata or {}

        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}

    def set_node_score(self, node_id: str, score_type: str, value: float):
        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}
        if node_id not in self.metadata["node_scores"]:
            self.metadata["node_scores"][node_id] = {}
        self.metadata["node_scores"][node_id][score_type] = value

    def get_node_score(self, node_id: str, score_type: str, default: float = 1.0) -> float:
        return self.metadata.get("node_scores", {}).get(node_id, {}).get(score_type, default)
    
    def set_pair_score(self, node_a: str, node_b: str, score_type: str, value: float, directed: bool = False):
        if "pair_scores" not in self.metadata:
            self.metadata["pair_scores"] = {}

        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        if pair_key not in self.metadata["pair_scores"]:
            self.metadata["pair_scores"][pair_key] = {}
        self.metadata["pair_scores"][pair_key][score_type] = value

    def get_pair_score(self, node_a: str, node_b: str, score_type: str, default: float = 0.0, directed: bool = False) -> float:
        pair_scores = self.metadata.get("pair_scores", {})
        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        return pair_scores.get(pair_key, {}).get(score_type, default)

    def __and__(self, other: 'DirectedHyperedge') -> 'DirectedHyperedge':
        """Intersection of directed hyperedges by common sources and targets"""
        common_sources = list(set(self.source_nodes) & set(other.source_nodes))
        common_targets = list(set(self.target_nodes) & set(other.target_nodes))
        return DirectedHyperedge(
            f"{self.edge_id}_intersect_{other.edge_id}",
            common_sources, common_targets, f"{self.modality}_{other.modality}"
        )

    def __add__(self, other: 'DirectedHyperedge') -> 'DirectedHyperedge':
        """Union of directed hyperedges by combining sources and targets"""
        all_sources = list(set(self.source_nodes) | set(other.source_nodes))
        all_targets = list(set(self.target_nodes) | set(other.target_nodes))
        return DirectedHyperedge(
            f"{self.edge_id}_union_{other.edge_id}",
            all_sources, all_targets, f"{self.modality}_{other.modality}"
        )
    
    def compute_features(self, node_dict: Dict[str, BaseNode]):
        connected_nodes = [
            node_dict[node_id]
            for node_id in self.source_nodes + self.target_nodes
            if node_id in node_dict
        ]
        super().compute_features(connected_nodes)


class NodeDirectedHyperedge(HyperedgeBase):
    """Node-directed hyperedge with PAG source and target node sets."""
    def __init__(
        self,
        edge_id: str,
        source_nodes: List[str],
        target_nodes: List[str],
        modality: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(edge_id, "node_directed", modality, weight)
        self.source_nodes = source_nodes
        self.target_nodes = target_nodes
        self.metadata = metadata or {}

        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}

    def set_node_score(self, node_id: str, score_type: str, value: float):
        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}
        if node_id not in self.metadata["node_scores"]:
            self.metadata["node_scores"][node_id] = {}
        self.metadata["node_scores"][node_id][score_type] = value

    def get_node_score(self, node_id: str, score_type: str, default: float = 1.0) -> float:
        return self.metadata.get("node_scores", {}).get(node_id, {}).get(score_type, default)

    def set_pair_score(self, node_a: str, node_b: str, score_type: str, value: float, directed: bool = False):
        if "pair_scores" not in self.metadata:
            self.metadata["pair_scores"] = {}

        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        if pair_key not in self.metadata["pair_scores"]:
            self.metadata["pair_scores"][pair_key] = {}
        self.metadata["pair_scores"][pair_key][score_type] = value

    def get_pair_score(self, node_a: str, node_b: str, score_type: str, default: float = 0.0, directed: bool = False) -> float:
        pair_scores = self.metadata.get("pair_scores", {})
        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        return pair_scores.get(pair_key, {}).get(score_type, default)
    
    def __and__(self, other: 'NodeDirectedHyperedge') -> 'NodeDirectedHyperedge':
        """Intersection of node-directed hyperedges by common sources and targets."""
        common_sources = list(set(self.source_nodes) & set(other.source_nodes))
        common_targets = list(set(self.target_nodes) & set(other.target_nodes))
        return NodeDirectedHyperedge(
            f"{self.edge_id}_intersect_{other.edge_id}",
            common_sources, common_targets, f"{self.modality}_{other.modality}"
        )

    def __add__(self, other: 'NodeDirectedHyperedge') -> 'NodeDirectedHyperedge':
        """Union of node-directed hyperedges by combining sources and targets."""
        all_sources = list(set(self.source_nodes) | set(other.source_nodes))
        all_targets = list(set(self.target_nodes) | set(other.target_nodes))
        return NodeDirectedHyperedge(
            f"{self.edge_id}_union_{other.edge_id}",
            all_sources, all_targets, f"{self.modality}_{other.modality}"
        )
    
    def compute_features(self, node_dict: Dict[str, BaseNode]):
        connected_nodes = [
            node_dict[node_id]
            for node_id in self.source_nodes + self.target_nodes
            if node_id in node_dict
        ]
        super().compute_features(connected_nodes)


# ===== Hyperedge Nesting Class ===== #

class NestingHyperedges(HyperedgeBase):
    """
    A hyperedge (aggregator) containing other hyperedges (Simple, Directed, NodeDirected,
    or more NestingHyperedges). Useful for hierarchical or multi-layered structures.

    The child's `edge_type` is NOT overridden; it remains 'simple', 'directed', etc.
    We simply add optional metadata to note that each child is nested within this aggregator.
    """
    def __init__(
        self,
        edge_id: str,
        hyperedges: List[HyperedgeBase],  # Could be Simple, Directed, NodeDirected, or Nesting
        modality: str,
        metadata: Dict[str, Any] = None,
        track_hierarchy: bool = True
    ):
        super().__init__(edge_id, "nesting", modality)
        self.hyperedges = hyperedges
        self.metadata = metadata or {}

        # Optionally store a record of how many children we have
        self.metadata["children_count"] = len(self.hyperedges)

        # If the user wants to track hierarchy, mark each child as nested
        if track_hierarchy:
            for child in self.hyperedges:
                self._tag_child_as_nested(child)

    def _tag_child_as_nested(self, child: HyperedgeBase):
        # 1) Mark the child as nested, if not already done
        if "nested" not in child.metadata:
            child.metadata["nested"] = True
        # 2) Preserve the child's original edge_type if not already stored
        if "original_edge_type" not in child.metadata:
            child.metadata["original_edge_type"] = child.edge_type
        # 3) Add this aggregator as a parent
        parents_list = child.metadata.get("nested_parents", [])
        if self.edge_id not in parents_list:
            parents_list.append(self.edge_id)
        child.metadata["nested_parents"] = parents_list
        # 4) The number of NestingHyperedges referencing this child
        child.metadata["parents_count"] = len(parents_list)

    def __and__(self, other: 'NestingHyperedges') -> 'NestingHyperedges':
        """Intersection of hyperedges common to both sets."""
        common_hyperedges = [e for e in self.hyperedges if e in other.hyperedges]
        return NestingHyperedges(
            f"{self.edge_id}_intersect_{other.edge_id}",
            common_hyperedges,
            f"{self.modality}_{other.modality}"
        )

    def __add__(self, other: 'NestingHyperedges') -> 'NestingHyperedges':
        """Union of hyperedges from both sets, deduplicated."""
        combined = list(set(self.hyperedges + other.hyperedges))
        return NestingHyperedges(
            f"{self.edge_id}_union_{other.edge_id}",
            combined,
            f"{self.modality}_{other.modality}"
        )

    # ========= Utility Methods =========

    def get_all_nested_hyperedges(self, recurse: bool = False) -> List[HyperedgeBase]:
        """
        Return the immediate child hyperedges by default.
        If recurse=True, traverse deeper if any child is also a NestingHyperedges.
        """
        results = []
        for he in self.hyperedges:
            results.append(he)
            if recurse and isinstance(he, NestingHyperedges):
                results.extend(he.get_all_nested_hyperedges(recurse=True))
        return results

    def find_duplicate_nodes(self, recurse: bool = False) -> List[str]:
        """Find nodes that appear in more than one child hyperedge."""
        child_hyperedges = self.get_all_nested_hyperedges(recurse=recurse)
        node_counts = Counter()
        for he in child_hyperedges:
            node_list = _get_hyperedge_nodes(he)
            for n in node_list:
                node_counts[n] += 1
        duplicates = [node for node, c in node_counts.items() if c > 1]
        return duplicates

    def find_duplicate_pairs(
        self, recurse: bool = False, respect_direction: bool = False
    ) -> List[Tuple[str, str]]:
        """Find node-pairs that appear in more than one child hyperedge."""
        child_hyperedges = self.get_all_nested_hyperedges(recurse=recurse)
        pair_counts = Counter()
        for he in child_hyperedges:
            pair_scores = he.metadata.get("pair_scores", {})
            for pair_key in pair_scores:
                pair_used = pair_key if respect_direction else tuple(sorted(pair_key))
                pair_counts[pair_used] += 1
        duplicates = [pair for pair, c in pair_counts.items() if c > 1]
        return duplicates

    def get_scores_for_duplicate_nodes(
        self, duplicates: List[str], recurse: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return structure:
        {
          nodeA: [
            {"hyperedge_id": <ID>, "scores": {...node_scores...}},
            ...
          ]
        }
        """
        child_hyperedges = self.get_all_nested_hyperedges(recurse=recurse)
        results = defaultdict(list)

        for node in duplicates:
            for he in child_hyperedges:
                node_list = _get_hyperedge_nodes(he)
                if node in node_list:
                    node_score = he.metadata.get("node_scores", {}).get(node, {})
                    results[node].append({
                        "hyperedge_id": he.edge_id,
                        "scores": node_score
                    })
        return dict(results)

    def get_scores_for_duplicate_pairs(
        self,
        duplicates: List[Tuple[str, str]],
        recurse: bool = False,
        respect_direction: bool = False
    ) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """
        Return structure:
        {
          (A,B): [
            {"hyperedge_id": <ID>, "scores": {...pair_scores...}},
            ...
          ]
        }
        """
        child_hyperedges = self.get_all_nested_hyperedges(recurse=recurse)
        results = defaultdict(list)

        for pair in duplicates:
            sorted_pair = tuple(sorted(pair)) if not respect_direction else pair
            for he in child_hyperedges:
                pair_scores = he.metadata.get("pair_scores", {})
                if respect_direction:
                    if pair in pair_scores:
                        results[pair].append({
                            "hyperedge_id": he.edge_id,
                            "scores": pair_scores[pair]
                        })
                    else:
                        node_list = _get_hyperedge_nodes(he)
                        if pair[0] in node_list and pair[1] in node_list:
                            results[pair].append({
                                "hyperedge_id": he.edge_id,
                                "scores": {}
                            })
                else:
                    if sorted_pair in pair_scores:
                        results[pair].append({
                            "hyperedge_id": he.edge_id,
                            "scores": pair_scores[sorted_pair]
                        })
                    else:
                        node_list = _get_hyperedge_nodes(he)
                        if pair[0] in node_list and pair[1] in node_list:
                            results[pair].append({
                                "hyperedge_id": he.edge_id,
                                "scores": {}
                            })
        return dict(results)

    def describe_nested_connectivity(
        self, recurse: bool = False, respect_direction: bool = False
    ) -> Dict[str, Any]:
        """
        Show how child hyperedges (and nested hyperedges if recurse=True)
        are connected by shared nodes or node-pairs.
        Return structure:
        {
          "he_id_1": [
            {
              "other_hyperedge_id": "he_id_2",
              "shared_nodes": [...],
              "shared_pairs": [...]
            },
            ...
          ]
        }
        """
        child_hyperedges = self.get_all_nested_hyperedges(recurse=recurse)
        connectivity = defaultdict(list)

        he_nodes_dict = {}
        he_pairs_dict = {}
        for he in child_hyperedges:
            he_nodes = _get_hyperedge_nodes(he)
            he_nodes_dict[he.edge_id] = he_nodes
            pair_scores = he.metadata.get("pair_scores", {})
            pair_key_set = set()
            for pk in pair_scores:
                pk_used = pk if respect_direction else tuple(sorted(pk))
                pair_key_set.add(pk_used)
            he_pairs_dict[he.edge_id] = pair_key_set

        for i, he1 in enumerate(child_hyperedges):
            for j, he2 in enumerate(child_hyperedges):
                if i >= j:
                    continue
                shared_nodes = list(he_nodes_dict[he1.edge_id] & he_nodes_dict[he2.edge_id])
                shared_pairs = list(he_pairs_dict[he1.edge_id] & he_pairs_dict[he2.edge_id])
                if shared_nodes or shared_pairs:
                    connectivity[he1.edge_id].append({
                        "other_hyperedge_id": he2.edge_id,
                        "shared_nodes": shared_nodes,
                        "shared_pairs": shared_pairs
                    })
                    connectivity[he2.edge_id].append({
                        "other_hyperedge_id": he1.edge_id,
                        "shared_nodes": shared_nodes,
                        "shared_pairs": shared_pairs
                    })
        return dict(connectivity)


#
# ===== Helper Function ===== #
#
def _get_hyperedge_nodes(hyperedge: HyperedgeBase) -> List[str]:
    """
    Retrieve the list of node IDs from a hyperedge, no assumptions about pair-scores.
    If 'hyperedge' is itself a NestingHyperedges, return the union of all child hyperedges' nodes.
    """
    if isinstance(hyperedge, SimpleHyperedge):
        return list(hyperedge.nodes)
    elif isinstance(hyperedge, DirectedHyperedge):
        return list(hyperedge.source_nodes + hyperedge.target_nodes)
    elif isinstance(hyperedge, NodeDirectedHyperedge):
        return list(hyperedge.source_nodes + hyperedge.target_nodes)
    elif isinstance(hyperedge, NestingHyperedges):
        all_nodes = set()
        for child in hyperedge.hyperedges:
            all_nodes.update(_get_hyperedge_nodes(child))
        return list(all_nodes)
    else:
        return []


class Partition:
    """Network partition based on shared attributes."""
    def __init__(self, partition_id: str, required_attributes: Set[str]):
        self.partition_id = partition_id
        self.required_attributes = required_attributes

        # Store nodes, hyperedges, and base edges separately.
        self.nodes: Dict[str, BaseNode] = {}
        self.hyperedges: Dict[str, HyperedgeBase] = {}
        self.base_edges: Dict[str, BaseEdge] = {}

    def add_node(self, node: BaseNode) -> bool:
        """
        Add a node to the partition if it satisfies required attributes.
        Returns True if added, False otherwise.
        """
        # Check if the node has all required attributes.
        if all(attr in node.attributes for attr in self.required_attributes):
            self.nodes[node.node_id] = node
            return True
        return False

    def add_hyperedge(self, edge: HyperedgeBase) -> bool:
        """
        Add a hyperedge if *all* of its nodes exist in self.nodes.
        For advanced metadata (node_scores/pair_scores), no special handling
        is required here—it's stored in edge.metadata.
        """
        # Figure out the node IDs the hyperedge references
        edge_node_ids = self._get_hyperedge_node_ids(edge)

        # Only add if all nodes are present in this partition
        if all(node_id in self.nodes for node_id in edge_node_ids):
            self.hyperedges[edge.edge_id] = edge
            return True
        return False

    def add_base_edge(self, edge: BaseEdge) -> bool:
        """
        Add a standard (non-hyper) base edge if both source and target nodes
        exist in self.nodes.
        The advanced metadata is stored in edge.metadata as needed.
        """
        if edge.source_id in self.nodes and edge.target_id in self.nodes:
            self.base_edges[edge.edge_id] = edge
            return True
        return False

    def filter_by_metadata(self, key: str, value: Any) -> Dict[str, Union[BaseEdge, HyperedgeBase]]:
        """
        Example utility: Return all edges (base or hyper) that have
        metadata[key] == value. If you want more complex checks,
        extend or add additional parameters.

        We skip node-based logic here, but you can do similarly for nodes if needed.
        """
        matching_edges = {}

        # Check BaseEdges
        for edge_id, base_edge in self.base_edges.items():
            # For advanced metadata, e.g. base_edge.metadata["scores"]["weight"] == ...
            # We'll do a simple check: base_edge.metadata.get(key) == value
            # Or if you store more structured data, adapt accordingly.
            if base_edge.metadata.get(key) == value:
                matching_edges[edge_id] = base_edge

        # Check Hyperedges
        for edge_id, hyperedge in self.hyperedges.items():
            if hyperedge.metadata.get(key) == value:
                matching_edges[edge_id] = hyperedge

        return matching_edges

    #
    # =========== Helper Methods ===========
    #

    def _get_hyperedge_node_ids(self, edge: HyperedgeBase) -> Set[str]:
        """
        Return the set of node IDs referenced by the hyperedge.
        Handles Simple/Directed/NodeDirected/NestingHyperedges.
        """
        if isinstance(edge, SimpleHyperedge):
            return set(edge.nodes)

        elif isinstance(edge, DirectedHyperedge):
            return set(edge.source_nodes + edge.target_nodes)

        elif isinstance(edge, NodeDirectedHyperedge):
            return set(edge.source_nodes + edge.target_nodes)

        elif isinstance(edge, NestingHyperedges):
            # Recursively collect all nodes from nested hyperedges
            return self._collect_nested_nodes(edge)

        else:
            return set()  # fallback if edge type is unknown

    def _collect_nested_nodes(self, aggregator: NestingHyperedges) -> Set[str]:
        """
        Recursively collect node IDs from a NestingHyperedges aggregator.
        """
        all_nodes = set()
        for child in aggregator.hyperedges:
            all_nodes.update(self._get_hyperedge_node_ids(child))
        return all_nodes



class Hypergraph:
    """Enhanced hypergraph supporting multiple node and edge types"""
    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        self.nodes: Dict[str, BaseNode] = {}
        self.edges: Dict[str, HyperedgeBase] = {}
        self.incidence_matrix: Optional[np.ndarray] = None

        # 1) Initialize partitions dict so create_partition(...) can store them
        self.partitions: Dict[str, Partition] = {}

    def add_node(self, node: BaseNode):
        self.nodes[node.node_id] = node

    def add_edge(
        self,
        edge: Union[SimpleHyperedge, DirectedHyperedge, NodeDirectedHyperedge, NestingHyperedges]
    ):
        """Add any hyperedge-based object to the hypergraph."""
        self.edges[edge.edge_id] = edge

    def compute_incidence_matrix(self):
        """Compute incidence matrix, including node-directed hyperedges."""
        num_nodes = len(self.nodes)
        num_edges = len(self.edges)
        matrix = np.zeros((num_nodes, num_edges))

        node_index_map = {node_id: idx for idx, node_id in enumerate(self.nodes.keys())}

        for e_idx, edge in enumerate(self.edges.values()):
            if isinstance(edge, SimpleHyperedge):
                for node_id in edge.nodes:
                    if node_id in node_index_map:
                        matrix[node_index_map[node_id], e_idx] = 1

            elif isinstance(edge, DirectedHyperedge):
                for node_id in edge.source_nodes:
                    if node_id in node_index_map:
                        matrix[node_index_map[node_id], e_idx] = -1
                for node_id in edge.target_nodes:
                    if node_id in node_index_map:
                        matrix[node_index_map[node_id], e_idx] = 1

            elif isinstance(edge, NodeDirectedHyperedge):
                for node_id in edge.source_nodes:
                    if node_id in node_index_map:
                        matrix[node_index_map[node_id], e_idx] = -1
                for node_id in edge.target_nodes:
                    if node_id in node_index_map:
                        matrix[node_index_map[node_id], e_idx] = 1

            # Optionally, you could define how you want to handle NestingHyperedges in the incidence matrix
            # e.g., ignoring them or summing nodes from all child hyperedges.

        self.incidence_matrix = matrix
        return matrix

    def concatenate_matrices(self, other: 'Hypergraph', axis: int = 0):
        """Concatenate incidence matrices with another hypergraph"""
        if self.incidence_matrix is None:
            self.compute_incidence_matrix()
        if other.incidence_matrix is None:
            other.compute_incidence_matrix()
        self.incidence_matrix = np.concatenate([self.incidence_matrix, other.incidence_matrix], axis=axis)

    def create_partition(self, partition_id: str, required_attributes: Set[str]) -> Partition:
        """
        Create and populate a partition based on required attributes.
        Updates to handle different hyperedge types (Simple, Directed, NodeDirected, Nesting).
        """
        partition = Partition(partition_id, required_attributes)

        # 2a) Partition the nodes
        for node in self.nodes.values():
            # The node must have *all* required attributes
            if all(attr in node.attributes for attr in required_attributes):
                partition.nodes[node.node_id] = node

        # 2b) Partition the edges
        for edge in self.edges.values():
            # Retrieve the relevant node IDs differently based on edge type
            if isinstance(edge, SimpleHyperedge):
                hyperedge_nodes = edge.nodes

            elif isinstance(edge, (DirectedHyperedge, NodeDirectedHyperedge)):
                hyperedge_nodes = edge.source_nodes + edge.target_nodes

            elif isinstance(edge, NestingHyperedges):
                # Flatten or gather all child nodes
                # Let's gather all nested nodes via a small helper
                hyperedge_nodes = _collect_all_nested_nodes(edge)

            else:
                # fallback
                hyperedge_nodes = []

            # Only add the edge if *all* of its nodes appear in the partition's nodes
            if all(node_id in partition.nodes for node_id in hyperedge_nodes):
                partition.edges[edge.edge_id] = edge

        self.partitions[partition_id] = partition
        return partition

    def query_metadata(self, key: str, value: Any) -> List[BaseNode]:
        """Find all nodes with a specific key-value pair in attributes or metadata."""
        return [
            node for node in self.nodes.values()
            if node.attributes.get(key.lower()) == value or node.metadata.get(key.lower()) == value
        ]

    def compute_degree_matrix(self):
        """
        Compute the degree matrix for the hypergraph (for Simple & Directed).
        If you want to incorporate NodeDirected or Nesting, define how.
        """
        num_nodes = len(self.nodes)
        degrees = np.zeros(num_nodes)
        node_indices = {node_id: idx for idx, node_id in enumerate(self.nodes.keys())}

        for edge in self.edges.values():
            if isinstance(edge, SimpleHyperedge):
                for node_id in edge.nodes:
                    degrees[node_indices[node_id]] += 1
            elif isinstance(edge, DirectedHyperedge):
                for node_id in edge.source_nodes:
                    degrees[node_indices[node_id]] += 1
                for node_id in edge.target_nodes:
                    degrees[node_indices[node_id]] += 1
            # optionally handle NodeDirectedHyperedge: same logic as Directed
            elif isinstance(edge, NodeDirectedHyperedge):
                for node_id in edge.source_nodes:
                    degrees[node_indices[node_id]] += 1
                for node_id in edge.target_nodes:
                    degrees[node_indices[node_id]] += 1

        return np.diag(degrees)

    def compute_adjacency_matrix(self):
        """
        Compute the adjacency matrix for the hypergraph.
        Now includes NodeDirectedHyperedge for completeness.
        """
        num_nodes = len(self.nodes)
        adjacency = np.zeros((num_nodes, num_nodes))
        node_indices = {node_id: idx for idx, node_id in enumerate(self.nodes.keys())}

        for edge in self.edges.values():
            if isinstance(edge, SimpleHyperedge):
                for i, node_a in enumerate(edge.nodes):
                    for j, node_b in enumerate(edge.nodes):
                        if i != j:
                            adjacency[node_indices[node_a], node_indices[node_b]] += edge.weight

            elif isinstance(edge, DirectedHyperedge):
                for source in edge.source_nodes:
                    for target in edge.target_nodes:
                        adjacency[node_indices[source], node_indices[target]] += edge.weight

            elif isinstance(edge, NodeDirectedHyperedge):
                for source in edge.source_nodes:
                    for target in edge.target_nodes:
                        adjacency[node_indices[source], node_indices[target]] += edge.weight

            # if you want to handle NestingHyperedges, define logic here

        return adjacency

    def compute_node_feature_matrix(self):
        """
        Compute the node feature matrix X.
        """
        feature_matrix = []
        for node in self.nodes.values():
            if node.feature_vector is None:
                node.compute_features()  # Compute features if not already done
            feature_matrix.append(node.feature_vector)
        return np.vstack(feature_matrix) if feature_matrix else np.array([])

    def compute_hyperedge_feature_matrix(self):
        """
        Compute the hyperedge feature matrix U by letting each edge compute features if not done.
        """
        feature_matrix = []
        for edge in self.edges.values():
            if edge.feature_vector is None:
                edge.compute_features(self.nodes)  # For Simple/Directed/NodeDirected
            feature_matrix.append(edge.feature_vector)
        return np.vstack(feature_matrix) if feature_matrix else np.array([])


#
# ========== Helper for create_partition with NestingHyperedges ========== #
#
def _collect_all_nested_nodes(hyperedge: NestingHyperedges) -> Set[str]:
    """
    Recursively collect all node IDs from a NestingHyperedges aggregator.
    """
    all_nodes = set()
    for child in hyperedge.hyperedges:
        if isinstance(child, SimpleHyperedge):
            all_nodes.update(child.nodes)
        elif isinstance(child, (DirectedHyperedge, NodeDirectedHyperedge)):
            all_nodes.update(child.source_nodes + child.target_nodes)
        elif isinstance(child, NestingHyperedges):
            all_nodes.update(_collect_all_nested_nodes(child))
        else:
            pass
    return all_nodes

class NestingHyperedgeMatrix:
    @staticmethod
    def flatten_to_hypergraph(nesting: NestingHyperedges) -> Hypergraph:
        """
        Flatten a nested hyperedge structure into a Hypergraph.
        """
        flattened_hypergraph = Hypergraph(graph_id="flattened")

        # Recursively add all nodes and edges
        def process_edge(edge: HyperedgeBase):
            if isinstance(edge, SimpleHyperedge):
                # Add nodes
                for node_id in edge.nodes:
                    if node_id not in flattened_hypergraph.nodes:
                        flattened_hypergraph.add_node(BaseNode(node_id, "entity"))
                flattened_hypergraph.add_edge(edge)

            elif isinstance(edge, DirectedHyperedge):
                # Add nodes
                for node_id in edge.source_nodes + edge.target_nodes:
                    if node_id not in flattened_hypergraph.nodes:
                        flattened_hypergraph.add_node(BaseNode(node_id, "entity"))
                flattened_hypergraph.add_edge(edge)

            elif isinstance(edge, NodeDirectedHyperedge):
                # Add nodes (NodeDirectedHyperedge is new!)
                for node_id in edge.source_nodes + edge.target_nodes:
                    if node_id not in flattened_hypergraph.nodes:
                        flattened_hypergraph.add_node(BaseNode(node_id, "entity"))
                flattened_hypergraph.add_edge(edge)

            elif isinstance(edge, NestingHyperedges):
                # Recur for nested hyperedges
                for nested in edge.hyperedges:
                    process_edge(nested)

        # Start recursion
        process_edge(nesting)
        return flattened_hypergraph

    @staticmethod
    def compute_degree_matrix(nodes, nested_edges: List[NestingHyperedges]):
        """
        Compute degree matrix for nested hyperedges.
        We flatten the first nested edge aggregator and compute degrees.
        """
        if not nested_edges:
            return np.array([])

        # Flatten the nested structure into a hypergraph
        hypergraph = NestingHyperedgeMatrix.flatten_to_hypergraph(nested_edges[0])
        return hypergraph.compute_degree_matrix()

    @staticmethod
    def compute_adjacency_matrix(nodes, nested_edges: List[NestingHyperedges]):
        """
        Compute adjacency matrix for nested hyperedges by flattening the first aggregator.
        """
        if not nested_edges:
            return np.array([])

        hypergraph = NestingHyperedgeMatrix.flatten_to_hypergraph(nested_edges[0])

        # Map node IDs to indices
        node_to_index = {node_id: idx for idx, node_id in enumerate(hypergraph.nodes.keys())}
        adjacency = np.zeros((len(nodes), len(nodes)))

        # Incorporate direct relationships
        for edge in hypergraph.edges.values():
            if isinstance(edge, SimpleHyperedge):
                for i, node_a in enumerate(edge.nodes):
                    for node_b in edge.nodes[i+1:]:
                        if node_a in node_to_index and node_b in node_to_index:
                            adjacency[node_to_index[node_a], node_to_index[node_b]] += 1
                            adjacency[node_to_index[node_b], node_to_index[node_a]] += 1

            elif isinstance(edge, DirectedHyperedge):
                for source_node in edge.source_nodes:
                    for target_node in edge.target_nodes:
                        if source_node in node_to_index and target_node in node_to_index:
                            adjacency[node_to_index[source_node], node_to_index[target_node]] += 1

            elif isinstance(edge, NodeDirectedHyperedge):
                for source_node in edge.source_nodes:
                    for target_node in edge.target_nodes:
                        if source_node in node_to_index and target_node in node_to_index:
                            adjacency[node_to_index[source_node], node_to_index[target_node]] += 1

        # Incorporate indirect relationships from all nested edges
        for aggregator in nested_edges:
            involved_nodes = list(NestingHyperedgeMatrix.flatten_nested_hyperedges(aggregator))
            for i, node_a in enumerate(involved_nodes):
                for node_b in involved_nodes[i+1:]:
                    if node_a in node_to_index and node_b in node_to_index:
                        adjacency[node_to_index[node_a], node_to_index[node_b]] += 1
                        adjacency[node_to_index[node_b], node_to_index[node_a]] += 1

        return adjacency

    @staticmethod
    def flatten_nested_hyperedges(nesting: NestingHyperedges) -> Set[str]:
        """
        Recursively flatten a NestingHyperedges aggregator to extract all contained node IDs.
        """
        all_nodes = set()
        for edge in nesting.hyperedges:
            if isinstance(edge, SimpleHyperedge):
                all_nodes.update(edge.nodes)
            elif isinstance(edge, DirectedHyperedge):
                all_nodes.update(edge.source_nodes)
                all_nodes.update(edge.target_nodes)
            elif isinstance(edge, NodeDirectedHyperedge):
                all_nodes.update(edge.source_nodes)
                all_nodes.update(edge.target_nodes)
            elif isinstance(edge, NestingHyperedges):
                all_nodes.update(NestingHyperedgeMatrix.flatten_nested_hyperedges(edge))
            # else: ignore or handle future edge types
        return all_nodes

#
# ===== Entity Graph Classes with Advanced Metadata and Queries =====
#

class EntityGraphNode:
    def __init__(
        self,
        node_id: str,
        attributes: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        EntityGraphNode can store attributes (lowercased for consistency)
        and an optional metadata dict for advanced usage.
        """
        self.node_id = node_id
        self.attributes = {k.lower(): v for k, v in attributes.items()}
        self.metadata = metadata or {}

    def __repr__(self):
        return (
            f"EntityGraphNode("
            f"id={self.node_id}, attributes={self.attributes}, metadata={self.metadata})"
        )


class EntityGraphEdge:
    def __init__(
        self,
        edge_id: str,
        connected_nodes: List[str],
        modality: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        EntityGraphEdge referencing one or more node IDs (connected_nodes).
        We also add a metadata dict for advanced usage, e.g.:
          - node_scores: { node_id: {score_type: value, ...}, ... }
          - pair_scores: { (nodeA,nodeB): {score_type: value, ...}, ... }
          - additional fields for 'weight', 'confidence', 'relevance', etc.
        """
        self.edge_id = edge_id
        self.connected_nodes = connected_nodes  # can be more than two
        self.modality = modality
        self.metadata = metadata or {}

        # Initialize sub-dicts for advanced scoring if they don't exist
        if "node_scores" not in self.metadata:
            self.metadata["node_scores"] = {}
        if "pair_scores" not in self.metadata:
            self.metadata["pair_scores"] = {}

    def __repr__(self):
        return (
            f"EntityGraphEdge("
            f"id={self.edge_id}, nodes={self.connected_nodes}, "
            f"modality={self.modality}, metadata={self.metadata})"
        )

    #
    # ===== Node-Level Scoring =====
    #
    def set_node_score(self, node_id: str, score_type: str, value: float):
        """
        Assign a particular score to a single node within this edge.
        Example: set_node_score("node1", "weight", 0.7).
        """
        if node_id not in self.metadata["node_scores"]:
            self.metadata["node_scores"][node_id] = {}
        self.metadata["node_scores"][node_id][score_type] = value

    def get_node_score(self, node_id: str, score_type: str, default: float = 0.0) -> float:
        """
        Retrieve a specific node-level score for this edge.
        """
        return self.metadata["node_scores"].get(node_id, {}).get(score_type, default)

    #
    # ===== Pair-Level Scoring =====
    #
    def set_pair_score(self, node_a: str, node_b: str, score_type: str, value: float, directed: bool = False):
        """
        Assign a particular score to a pair of nodes within this edge.
        If 'directed' is False, store the pair in a canonical (sorted) order,
        else store (node_a, node_b) exactly.
        """
        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)

        if pair_key not in self.metadata["pair_scores"]:
            self.metadata["pair_scores"][pair_key] = {}
        self.metadata["pair_scores"][pair_key][score_type] = value

    def get_pair_score(self, node_a: str, node_b: str, score_type: str, default: float = 0.0, directed: bool = False):
        """
        Retrieve a specific pair-level score for this edge.
        """
        if not directed:
            pair_key = tuple(sorted([node_a, node_b]))
        else:
            pair_key = (node_a, node_b)
        return self.metadata["pair_scores"].get(pair_key, {}).get(score_type, default)

    def set_all_pair_scores(self, score_type: str, value: float, directed: bool = False):
        """
        Assign the same score (score_type) to every distinct pair of connected_nodes.
        If 'directed' is False, (nodeA,nodeB) is stored in sorted order.
        """
        # If connected_nodes has length > 2, we automatically set pair scores for all combinations
        from itertools import combinations
        node_ids = self.connected_nodes
        for (nA, nB) in combinations(node_ids, 2):
            self.set_pair_score(nA, nB, score_type, value, directed=directed)


class EntitySpecificGraph:
    """Graph representing a single entity's network"""
    def __init__(self, graph_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Optionally store metadata at the graph level for advanced usage.
        """
        self.graph_name = graph_name
        self.nodes: Dict[str, EntityGraphNode] = {}
        self.edges: Dict[str, EntityGraphEdge] = {}
        self.metadata = metadata or {}

    def add_node(self, node: EntityGraphNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: EntityGraphEdge):
        self.edges[edge.edge_id] = edge

    #
    # ===== Extended Queries for Nodes =====
    #

    def query_nodes_by_metadata(self, key: str, value: Any) -> List[EntityGraphNode]:
        """
        Find nodes for which node.metadata[key] == value.
        """
        matches = []
        for node in self.nodes.values():
            if node.metadata.get(key) == value:
                matches.append(node)
        return matches

    def query_nodes_by_attributes(self, key: str, value: Any) -> List[EntityGraphNode]:
        """
        Find nodes for which node.attributes[key] == value
        (case-insensitive if you store keys in lower).
        """
        matches = []
        for node in self.nodes.values():
            if node.attributes.get(key.lower()) == value:
                matches.append(node)
        return matches

    def query_nodes_by_attribute_or_metadata(self, key: str, value: Any) -> List[EntityGraphNode]:
        """
        Combined search in both node.attributes and node.metadata.
        """
        matches = []
        for node in self.nodes.values():
            if node.attributes.get(key.lower()) == value or node.metadata.get(key) == value:
                matches.append(node)
        return matches

    #
    # ===== Extended Queries for Edges =====
    #

    def query_edges_by_metadata(self, key: str, value: Any) -> List[EntityGraphEdge]:
        """
        Return edges where edge.metadata[key] == value.
        """
        results = []
        for edge in self.edges.values():
            if edge.metadata.get(key) == value:
                results.append(edge)
        return results

    def find_edges_by_node_score_threshold(self, node_id: str, score_type: str, min_score: float) -> List[EntityGraphEdge]:
        """
        Return edges where get_node_score(node_id, score_type) >= min_score.
        """
        results = []
        for edge in self.edges.values():
            score = edge.get_node_score(node_id, score_type, 0.0)
            if score >= min_score:
                results.append(edge)
        return results

    #
    # ===== Existing Methods =====
    #

    def find_shared_attributes(self, other_graph: 'EntitySpecificGraph', regex_pattern: str = None) -> Set[str]:
        """
        Find shared attributes across nodes in this graph and another graph.
        This method only checks node.attributes (not node.metadata).
        """
        shared_attributes = set()

        # Step 1: Group attributes by category for this graph
        self_attr_by_category = {}
        for node in self.nodes.values():
            for attr, value in node.attributes.items():
                if attr not in self_attr_by_category:
                    self_attr_by_category[attr] = set()
                if isinstance(value, list):
                    self_attr_by_category[attr].update(value)
                else:
                    self_attr_by_category[attr].add(value)

        # Step 2: Group attributes by category for the other graph
        other_attr_by_category = {}
        for other_node in other_graph.nodes.values():
            for attr, value in other_node.attributes.items():
                if attr not in other_attr_by_category:
                    other_attr_by_category[attr] = set()
                if isinstance(value, list):
                    other_attr_by_category[attr].update(value)
                else:
                    other_attr_by_category[attr].add(value)

        # Step 3: Find common attributes by category
        for attr, self_values in self_attr_by_category.items():
            if attr in other_attr_by_category:
                other_values = other_attr_by_category[attr]
                if regex_pattern:
                    regex = re.compile(regex_pattern, re.IGNORECASE)
                    shared_values = {
                        val for val in self_values
                        if any(regex.match(str(ov)) for ov in other_values)
                    }
                else:
                    shared_values = self_values.intersection(other_values)
                shared_attributes.update(shared_values)

        return shared_attributes


class MultilayerNetwork:
    """Network managing multiple entity-specific graphs"""
    def __init__(self):
        self.entity_graphs: Dict[str, EntitySpecificGraph] = {}

    def add_entity_graph(self, entity_graph: EntitySpecificGraph):
        self.entity_graphs[entity_graph.graph_name] = entity_graph

    def perform_cross_layer_analysis(self, regex_pattern: Optional[str] = None) -> Dict[str, Set[str]]:
        """Analyze shared attributes across all entity-specific graphs, node-level only."""
        intersections = {}
        graph_list = list(self.entity_graphs.values())
        for i in range(len(graph_list)):
            for j in range(i + 1, len(graph_list)):
                shared = graph_list[i].find_shared_attributes(graph_list[j], regex_pattern)
                if shared:
                    intersections[f"{graph_list[i].graph_name} & {graph_list[j].graph_name}"] = shared
        return intersections

    #
    # ===== Optional Advanced Queries Across Entity Graphs =====
    #
    def query_edge_metadata_across_graphs(self, key: str, value: Any) -> Dict[str, List[EntityGraphEdge]]:
        """
        Return edges from each entity graph whose edge.metadata[key] == value.
        """
        results = {}
        for graph_name, egraph in self.entity_graphs.items():
            matching_edges = egraph.query_edges_by_metadata(key, value)
            if matching_edges:
                results[graph_name] = matching_edges
        return results

    def find_edges_by_node_score_threshold_across_graphs(
        self, node_id: str, score_type: str, min_score: float
    ) -> Dict[str, List[EntityGraphEdge]]:
        """
        Return edges from each entity graph where node_id's score >= min_score.
        """
        results = {}
        for graph_name, egraph in self.entity_graphs.items():
            matching_edges = egraph.find_edges_by_node_score_threshold(node_id, score_type, min_score)
            if matching_edges:
                results[graph_name] = matching_edges
        return results

class UnifiedGraphFramework:
    """Framework integrating hypergraphs and entity-specific graphs"""
    def __init__(self):
        self.hypergraph_network = Hypergraph(graph_id="main_hypergraph")  # Provide a graph_id
        self.multilayer_network = MultilayerNetwork()

    def convert_entity_graph_to_hypergraph(self, entity_graph: EntitySpecificGraph) -> Hypergraph:
        """
        Convert an EntitySpecificGraph into a Hypergraph.
        - Preserves advanced metadata in nodes/edges by storing them in BaseNode/Hyperedge metadata.
        - If you want to handle multiple hyperedge types, you can add logic for DirectedHyperedge, etc.
        """
        hypergraph = Hypergraph(graph_id=f"hg_{entity_graph.graph_name}")

        # 1) Convert Nodes
        for node in entity_graph.nodes.values():
            # Create a BaseNode that preserves node.attributes and node.metadata
            base_node = BaseNode(
                node_id=node.node_id,
                node_type="entity",
                attributes=node.attributes,
                metadata=node.metadata  # carry over advanced node metadata
            )
            hypergraph.add_node(base_node)

        # 2) Convert Edges
        #   We'll assume the user might store "source_nodes"/"target_nodes" in edge.attributes
        #   or rely on 'connected_nodes' as usual. Also carry over edge.metadata if present.
        for edge in entity_graph.edges.values():
            # if the user has "source_nodes" and "target_nodes" in edge.attributes, treat as NodeDirectedHyperedge
            if (
                isinstance(edge.attributes, dict) and
                "source_nodes" in edge.attributes and
                "target_nodes" in edge.attributes
            ):
                # Optionally, if you want to treat them as 'DirectedHyperedge' vs. 'NodeDirectedHyperedge',
                # you can decide here.
                base_edge = NodeDirectedHyperedge(
                    edge_id=edge.edge_id,
                    source_nodes=edge.attributes["source_nodes"],
                    target_nodes=edge.attributes["target_nodes"],
                    modality=edge.modality,
                    metadata=edge.metadata  # carry over edge-level advanced metadata
                )
            else:
                # Fallback: treat as SimpleHyperedge
                # If you want a DirectedHyperedge logic, you can add another check, e.g.
                # if edge.metadata.get("edge_type") == "directed": ...
                base_edge = SimpleHyperedge(
                    edge_id=edge.edge_id,
                    nodes=edge.connected_nodes,
                    modality=edge.modality,
                    metadata=edge.metadata
                )

            hypergraph.add_edge(base_edge)

        return hypergraph

    def convert_hypergraph_to_entity_graph(self, hypergraph: Hypergraph, graph_name: str) -> EntitySpecificGraph:
        """
        Convert a Hypergraph back to an EntitySpecificGraph.
        - Preserves advanced metadata by attaching it to EntityGraphNode or EntityGraphEdge.
        - Splits SimpleHyperedge into pairwise edges, and NodeDirectedHyperedge into one edge per source->target.
        """
        entity_graph = EntitySpecificGraph(graph_name=graph_name)

        # 1) Convert BaseNodes into EntityGraphNodes
        for node_id, base_node in hypergraph.nodes.items():
            entity_node = EntityGraphNode(
                node_id=node_id,
                attributes=base_node.attributes,
                metadata=base_node.metadata  # preserve advanced node metadata
            )
            entity_graph.add_node(entity_node)

        # 2) Convert Hyperedges into EntityGraphEdges
        #   - For SimpleHyperedge, break it into pairwise edges
        #   - For NodeDirectedHyperedge (and optionally DirectedHyperedge), create edges from source->target
        for edge_id, hyperedge in hypergraph.edges.items():
            if isinstance(hyperedge, SimpleHyperedge):
                # Create pairwise edges for each distinct node pair
                for i in range(len(hyperedge.nodes)):
                    for j in range(i + 1, len(hyperedge.nodes)):
                        new_edge = EntityGraphEdge(
                            edge_id=f"{edge_id}_e{i}_{j}",
                            connected_nodes=[hyperedge.nodes[i], hyperedge.nodes[j]],
                            modality=hyperedge.modality,
                            metadata=hyperedge.metadata  # carry over advanced edge metadata
                        )
                        entity_graph.add_edge(new_edge)

            elif isinstance(hyperedge, NodeDirectedHyperedge):
                # Create edges for each source->target pair
                for source_node in hyperedge.source_nodes:
                    for target_node in hyperedge.target_nodes:
                        new_edge = EntityGraphEdge(
                            edge_id=f"{edge_id}_{source_node}_{target_node}",
                            connected_nodes=[source_node, target_node],
                            modality=hyperedge.modality,
                            metadata=hyperedge.metadata
                        )
                        entity_graph.add_edge(new_edge)

            elif isinstance(hyperedge, DirectedHyperedge):
                # If you also want to handle DirectedHyperedge distinctly
                for source_node in hyperedge.source_nodes:
                    for target_node in hyperedge.target_nodes:
                        new_edge = EntityGraphEdge(
                            edge_id=f"{edge_id}_{source_node}_{target_node}",
                            connected_nodes=[source_node, target_node],
                            modality=hyperedge.modality,
                            metadata=hyperedge.metadata
                        )
                        entity_graph.add_edge(new_edge)
            # If you have NestingHyperedges, you might handle them differently or skip them here.

        return entity_graph

    def integrate_entity_graph(self, entity_graph: EntitySpecificGraph):
        """
        Integrate an entity graph into the 'main_hypergraph'.
        We convert the entity graph to a sub-hypergraph, then store it
        as a single BaseNode in the main hypergraph (embedding the sub-hypergraph in node metadata).
        """
        sub_hypergraph = self.convert_entity_graph_to_hypergraph(entity_graph)

        # Create a 'BaseNode' representing this sub-hypergraph
        # We embed the sub-hypergraph object inside node.metadata so we can retrieve it later.
        embedding_node = BaseNode(
            node_id=sub_hypergraph.graph_id,
            node_type="hypergraph",
            attributes={},  # no PAG attributes
            metadata={"embedded_hypergraph": sub_hypergraph}
        )
        self.hypergraph_network.add_node(embedding_node)

class HetNet:
    """A heterogeneous network supports multiple node and edge types."""
    def __init__(self, graph_id: str):
        self.graph_id = graph_id
        self.nodes: Dict[str, BaseNode] = {}
        # Store edges as a dict of edge_id -> BaseEdge
        self.edges: Dict[str, BaseEdge] = {}
        # Optionally track an internal counter for edge IDs if needed
        self._edge_counter = 0

    def add_node(self, node: BaseNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: BaseEdge):
        """
        Add a BaseEdge to the HetNet, ensuring source/target nodes exist.
        Raises ValueError if either node is missing.
        """
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError(f"Source or target node does not exist in the HetNet. "
                             f"{edge.source_id}, {edge.target_id}")
        self.edges[edge.edge_id] = edge

    def from_dataframe(self, df: pd.DataFrame, node_columns: List[str], edge_columns: List[str]):
        """
        Construct a HetNet from a pandas DataFrame.
        - `node_columns`: Columns to be used for nodes (strings identifying node IDs).
        - `edge_columns`: [source_col, target_col, ...extra_edge_attrs].
        """
        # 1) Create nodes
        for col in node_columns:
            for node_id in df[col].unique():
                if node_id not in self.nodes:
                    # You could store advanced node attributes/metadata if desired.
                    self.add_node(BaseNode(node_id, "entity", {}))

        # 2) Create edges
        for _, row in df.iterrows():
            source = row[edge_columns[0]]
            target = row[edge_columns[1]]
            # All remaining columns beyond [0],[1] are stored in metadata
            extra_attrs = {col: row[col] for col in edge_columns[2:]}

            edge_id = f"edge_{self._edge_counter}"
            self._edge_counter += 1

            edge = BaseEdge(
                edge_id=edge_id,
                source_id=source,
                target_id=target,
                metadata=extra_attrs  # store in metadata dict
            )
            self.add_edge(edge)


#
# ===== HetNet to Hypergraph Conversion ===== #
#

def hetnet_to_hypergraph(hetnet: HetNet, graph_id: str, clustering_method=None) -> Hypergraph:
    """
    Convert a HetNet into a Hypergraph by detecting appropriate hyperedge classes.
    - `clustering_method`: Optional function for grouping nodes. 
      If provided, we create hyperedges from those clusters. 
      Otherwise, each BaseEdge is turned into a hyperedge whose type we detect from metadata.
    """
    hypergraph = Hypergraph(graph_id)

    # 1) Add HetNet nodes to the Hypergraph
    for node in hetnet.nodes.values():
        # Reuse the same BaseNode (preserving attributes/metadata)
        hypergraph.add_node(node)

    # 2) If we have a clustering method, we cluster. Otherwise, convert each BaseEdge
    if clustering_method:
        clusters = clustering_method(hetnet.nodes, hetnet.edges)
        for idx, cluster in enumerate(clusters):
            # We treat these cluster-based hyperedges as 'simple' multi-node hyperedges
            hyperedge = SimpleHyperedge(
                edge_id=f"he_cluster_{idx}",
                nodes=list(cluster),
                modality="cluster"  # or something relevant
            )
            hypergraph.add_edge(hyperedge)
    else:
        # Default: Turn each BaseEdge into a hyperedge
        for edge_id, base_edge in hetnet.edges.items():
            # Detect hyperedge type from metadata or from presence of keys
            hyperedge = _create_hyperedge_from_base_edge(base_edge)
            hypergraph.add_edge(hyperedge)

    return hypergraph


def _create_hyperedge_from_base_edge(base_edge: BaseEdge) -> HyperedgeBase:
    """
    Logic to detect which hyperedge subclass to create from a BaseEdge,
    based on 'edge_type' or presence of 'source_nodes', 'target_nodes', etc.
    """
    # 1) Retrieve 'edge_type' from metadata if present
    edge_type = base_edge.metadata.get("edge_type", "simple").lower()
    modality = base_edge.metadata.get("modality", "default")

    # 2) If you store node sets in base_edge.metadata, gather them
    #    Otherwise, we assume it's a 2-node edge: [source_id, target_id]
    source_nodes = base_edge.metadata.get("source_nodes", [])
    target_nodes = base_edge.metadata.get("target_nodes", [])

    # Fallback for a typical 2-node edge if no special metadata
    # For example, "connected_nodes" might be in the metadata, or we just do [base_edge.source_id, base_edge.target_id].
    fallback_nodes = [base_edge.source_id, base_edge.target_id]

    # 3) Create the appropriate hyperedge
    if edge_type == "directed":
        # Possibly we expect 'source_nodes' / 'target_nodes' in metadata
        # If not present, fallback to single source/target
        if not source_nodes:
            source_nodes = [base_edge.source_id]
        if not target_nodes:
            target_nodes = [base_edge.target_id]

        return DirectedHyperedge(
            edge_id=f"he_{base_edge.edge_id}",
            source_nodes=source_nodes,
            target_nodes=target_nodes,
            modality=modality,
            metadata=base_edge.metadata
        )

    elif edge_type == "node_directed":
        # Similar logic
        if not source_nodes:
            source_nodes = [base_edge.source_id]
        if not target_nodes:
            target_nodes = [base_edge.target_id]

        return NodeDirectedHyperedge(
            edge_id=f"he_{base_edge.edge_id}",
            source_nodes=source_nodes,
            target_nodes=target_nodes,
            modality=modality,
            metadata=base_edge.metadata
        )

    elif edge_type == "simple":
        # Maybe the user sets multiple nodes in metadata["connected_nodes"]
        # or else fallback to [source_id, target_id]
        connected_nodes = base_edge.metadata.get("connected_nodes", fallback_nodes)
        return SimpleHyperedge(
            edge_id=f"he_{base_edge.edge_id}",
            nodes=connected_nodes,
            modality=modality,
            metadata=base_edge.metadata
        )

    else:
        # Default to SimpleHyperedge if unrecognized
        connected_nodes = base_edge.metadata.get("connected_nodes", fallback_nodes)
        return SimpleHyperedge(
            edge_id=f"he_{base_edge.edge_id}",
            nodes=connected_nodes,
            modality=modality,
            metadata=base_edge.metadata
        )

def create_hypergraph_hetnet(hypergraphs: List[Hypergraph], hetnet_id: str) -> HetNet:
    """
    Create a HetNet where each Hypergraph is represented as a node 
    and edges between Hypergraphs reflect similarity or other metrics.
    """
    hypergraph_hetnet = HetNet(hetnet_id)

    # 1) Add each hypergraph as a node in the HetNet
    for hg in hypergraphs:
        # Optionally store more advanced info in metadata if desired
        node_metadata = {
            "hypergraph_embedded": True,
            # Additional fields if you want, e.g. a reference to the 'hg' object
        }

        hypergraph_node = BaseNode(
            node_id=hg.graph_id,
            node_type="hypergraph",
            # Basic attributes capturing some stats about the hypergraph
            attributes={"size": len(hg.nodes), "edge_count": len(hg.edges)},
            metadata=node_metadata
        )
        hypergraph_hetnet.add_node(hypergraph_node)

    # 2) Add BaseEdges between hypergraphs based on embeddings/similarity
    #    or any other metric you compute.
    for i, hg1 in enumerate(hypergraphs):
        for j in range(i + 1, len(hypergraphs)):
            hg2 = hypergraphs[j]

            # Placeholder function to compute similarity
            similarity = compute_hypergraph_similarity(hg1, hg2)
            if similarity > 0.5:  # Example threshold
                # We create a BaseEdge that references the two "node_ids" in the HetNet
                # (which are actually the Hypergraph IDs).
                edge_id = f"edge_{hg1.graph_id}_{hg2.graph_id}"

                # In metadata, store 'similarity' plus optional 'edge_type' or 'modality'
                # so that if you later convert this HetNet to a Hypergraph, you can detect
                # an appropriate hyperedge type. 
                metadata = {
                    "similarity": similarity,
                    # For detection by _create_hyperedge_from_base_edge, for instance:
                    "edge_type": "simple",    # or "directed"/"node_directed"/"hypergraph_link"
                    "modality": "hypergraph_link"
                }

                base_edge = BaseEdge(
                    edge_id=edge_id,
                    source_id=hg1.graph_id,
                    target_id=hg2.graph_id,
                    metadata=metadata
                )
                hypergraph_hetnet.add_edge(base_edge)

    return hypergraph_hetnet

class BaseAlgorithm(ABC):
    """Abstract base class for hypergraph algorithms."""
    
    def __init__(self, hypergraph):
        self.hypergraph = hypergraph  # Reference to the hypergraph
    
    @abstractmethod
    def run(self, *args, **kwargs):
        """Abstract method to be implemented by subclasses."""
        pass


class PathFindingAlgorithm:
    """
    Path finding algorithm over a Hypergraph, focusing on node-based traversal.
    Incorporates logic for SimpleHyperedge, DirectedHyperedge, and NodeDirectedHyperedge.
    """

    def __init__(self, hypergraph):
        self.hypergraph = hypergraph

    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Find the shortest path (in terms of sum of weights) using Dijkstra's algorithm.
        If there's no path, returns None.
        """
        if source not in self.hypergraph.nodes or target not in self.hypergraph.nodes:
            return None

        # Priority queue holds tuples of (distance, current_node, path)
        from heapq import heappop, heappush
        pq = [(0.0, source, [source])]
        visited = set()
        distances = {node_id: float('inf') for node_id in self.hypergraph.nodes}
        distances[source] = 0.0

        while pq:
            current_dist, current_node, path = heappop(pq)
            if current_node == target:
                return path  # We found the shortest path

            if current_node in visited:
                continue
            visited.add(current_node)

            # Explore neighbors: check each hyperedge for adjacency
            for edge in self.hypergraph.edges.values():
                edge_weight = self._get_effective_weight(edge)

                # 1) SimpleHyperedge
                if isinstance(edge, SimpleHyperedge) and current_node in edge.nodes:
                    neighbors = edge.nodes

                # 2) DirectedHyperedge
                elif isinstance(edge, DirectedHyperedge):
                    neighbors = []
                    if current_node in edge.source_nodes:
                        neighbors = edge.target_nodes
                    elif current_node in edge.target_nodes:
                        neighbors = edge.source_nodes

                # 3) NodeDirectedHyperedge
                elif isinstance(edge, NodeDirectedHyperedge):
                    neighbors = []
                    # Similar logic to DirectedHyperedge
                    if current_node in edge.source_nodes:
                        neighbors = edge.target_nodes
                    elif current_node in edge.target_nodes:
                        neighbors = edge.source_nodes
                else:
                    # Edge type not relevant for adjacency from this current_node
                    continue

                # Evaluate potential neighbors
                for neighbor in neighbors:
                    if neighbor == current_node or neighbor in visited:
                        continue

                    new_dist = current_dist + edge_weight
                    if new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        heappush(pq, (new_dist, neighbor, path + [neighbor]))

        return None  # No path found

    def _get_effective_weight(self, edge) -> float:
        """
        Retrieve the effective weight of an edge, checking metadata if present.
        Falls back to edge.weight otherwise.
        """
        # Example: If you store advanced scoring in edge.metadata["scores"]["weight"]
        scores = edge.metadata.get("scores", {})
        return scores.get("weight", edge.weight)

    #
    # ===== Path Evaluation Methods =====
    #

    def evaluate_path_length(self, path: List[str]) -> int:
        """
        Evaluate the length of the path in terms of edges traversed.
        i.e., path of [A,B,C] => length 2
        """
        return len(path) - 1 if path else 0

    def evaluate_path_weight(self, path: List[str]) -> float:
        """
        Sum the weight of edges along the path. We handle SimpleHyperedge,
        DirectedHyperedge, and NodeDirectedHyperedge in a manner similar to find_shortest_path.
        """
        total_weight = 0.0
        if not path:
            return total_weight

        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]

            # Locate the edge that connects source->target (or target->source in the relevant hyperedge type)
            for edge in self.hypergraph.edges.values():
                edge_weight = self._get_effective_weight(edge)

                # 1) SimpleHyperedge: both nodes must be in edge.nodes
                if isinstance(edge, SimpleHyperedge):
                    if source in edge.nodes and target in edge.nodes:
                        total_weight += edge_weight
                        break

                # 2) DirectedHyperedge: source must be in source_nodes, target must be in target_nodes
                elif isinstance(edge, DirectedHyperedge):
                    if source in edge.source_nodes and target in edge.target_nodes:
                        total_weight += edge_weight
                        break
                    # If you allow reverse traversal for an undirected sense, handle that here if needed.

                # 3) NodeDirectedHyperedge: similar to DirectedHyperedge
                elif isinstance(edge, NodeDirectedHyperedge):
                    if source in edge.source_nodes and target in edge.target_nodes:
                        total_weight += edge_weight
                        break

        return total_weight

    def evaluate_path_connectivity(self, path: List[str]) -> int:
        """
        Evaluate how many valid connections exist along the path.
        Each consecutive pair (nodeA, nodeB) in path is counted if there's a valid hyperedge connecting them.
        """
        connectivity_score = 0
        if not path:
            return connectivity_score

        for i in range(len(path) - 1):
            node_a = path[i]
            node_b = path[i + 1]

            for edge in self.hypergraph.edges.values():
                # 1) SimpleHyperedge
                if isinstance(edge, SimpleHyperedge):
                    if node_a in edge.nodes and node_b in edge.nodes:
                        connectivity_score += 1
                        break
                # 2) DirectedHyperedge
                elif isinstance(edge, DirectedHyperedge):
                    if node_a in edge.source_nodes and node_b in edge.target_nodes:
                        connectivity_score += 1
                        break
                # 3) NodeDirectedHyperedge
                elif isinstance(edge, NodeDirectedHyperedge):
                    if node_a in edge.source_nodes and node_b in edge.target_nodes:
                        connectivity_score += 1
                        break
                # If there's no match, we don't increment
        return connectivity_score

from heapq import heappop, heappush
from typing import Optional, List, Dict, Union

class MultiHopTraversal(PathFindingAlgorithm):
    """
    Advanced multi-hop traversal algorithm incorporating a priority queue and
    edge scores (α * β) for each edge. Paths are pruned if their cumulative score < 'tau'.
    """

    def find_paths(
        self,
        start_node: str,
        end_node_type: Optional[str] = None,
        tau: float = 0.05,
        max_hops: int = 3,
        collect_all: bool = True
    ) -> List[Dict[str, Union[List[str], float]]]:
        """
        Find high-scoring paths from 'start_node' to any node whose type matches 'end_node_type',
        using a priority queue to expand highest-scoring paths first. 
        If 'end_node_type' is None, we simply expand up to 'max_hops' and collect all paths that meet 'tau'.

        Args:
            start_node (str): The node ID from which to begin traversal.
            end_node_type (str, optional): The node_type we consider a 'target' (e.g., 'drug'). 
                If None, we won't filter by node_type at the end; we just gather all expansions that meet 'tau'.
            tau (float): A threshold in (0,1]. Paths with cumulative score < tau are pruned.
            max_hops (int): Maximum path length (number of edges).
            collect_all (bool): If True, we collect all valid paths up to 'max_hops'. 
                Otherwise, you could stop after finding the first or top N.

        Returns:
            List[Dict[str, Union[List[str], float]]]: A list of results, where each result is:
                {
                    "path": [...list of node IDs...],
                    "score": <cumulative path score>
                }
            sorted in descending order by "score".
        """
        if start_node not in self.hypergraph.nodes:
            return []

        # If end_node_type is used, verify we have node_type in each node's definition
        # or handle it gracefully if missing.
        results = []

        # We store paths in a priority queue: (-path_score, path_list)
        # Negative because Python's heapq is a min-heap; we want max-heap behavior.
        pq = []
        # Start with path = [start_node], score = 1.0
        heappush(pq, (-1.0, [start_node]))

        visited_paths = set()  # optional: to avoid re-expanding identical paths
        while pq:
            neg_score, path = heappop(pq)
            path_score = -neg_score
            current_node = path[-1]

            # If we are using end_node_type, check if current_node meets it and path_score >= tau
            # If so, we can store the path as a valid result.
            # Or if end_node_type is None, any node with path_score >= tau could be "valid".
            node_obj = self.hypergraph.nodes.get(current_node)
            if node_obj and path_score >= tau:
                # If no end_node_type is set, or if node_obj.node_type == end_node_type, record result.
                if (end_node_type is None) or (node_obj.node_type == end_node_type):
                    results.append({"path": path.copy(), "score": path_score})
                    if not collect_all:
                        # If we only wanted the first success, we could break here
                        pass

            # If path length >= max_hops, don't expand further
            if (len(path) - 1) >= max_hops:
                continue

            # Explore neighbors from current_node by looking at all edges
            for edge in self.hypergraph.edges.values():
                # We get the edge's alpha/beta from metadata or default to 1
                alpha = edge.metadata.get("scores", {}).get("alpha", 1.0)
                beta = edge.metadata.get("scores", {}).get("beta", 1.0)
                edge_score = alpha * beta

                # Identify neighbors based on hyperedge type
                neighbors = []

                if isinstance(edge, SimpleHyperedge) and current_node in edge.nodes:
                    neighbors = edge.nodes

                elif isinstance(edge, DirectedHyperedge):
                    if current_node in edge.source_nodes:
                        neighbors = edge.target_nodes
                    elif current_node in edge.target_nodes:
                        neighbors = edge.source_nodes

                elif isinstance(edge, NodeDirectedHyperedge):
                    if current_node in edge.source_nodes:
                        neighbors = edge.target_nodes
                    elif current_node in edge.target_nodes:
                        neighbors = edge.source_nodes

                # Expand to each neighbor
                for nbr in neighbors:
                    if nbr == current_node:
                        continue
                    if nbr in path:
                        # optional: skip if we don't want cycles
                        continue

                    new_score = path_score * edge_score
                    # If new_score < tau, prune
                    if new_score < tau:
                        continue

                    new_path = path + [nbr]
                    path_key = (tuple(new_path), round(new_score, 6))
                    if path_key in visited_paths:
                        # Skip repeated expansions
                        continue
                    visited_paths.add(path_key)

                    # Push into the priority queue
                    heappush(pq, (-new_score, new_path))

        # Sort final results by descending score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

class DynamicMultiHopTraversal:
    """
    A universal multi-hop traversal algorithm supporting edge scoring (alpha*beta) 
    and threshold-based pruning. Uses an adapter to handle different graph types 
    (hypergraph, HetNet, entity-specific graph, etc.).

    Features:
      - Priority queue expansion of highest-score paths.
      - Prunes paths whose cumulative score < `tau`.
      - Limits path length to `max_hops`.
      - Optionally filters final nodes by `end_node_type`.
      - Has an option `collect_all` to either gather all valid paths or stop early.
    """

    def __init__(self, graph_adapter, tau: float = 0.05, max_hops: int = 3):
        """
        Args:
            graph_adapter: An object providing:
                - is_valid_node(node_id) -> bool
                - get_node_type(node_id) -> str
                - get_neighbors(node_id) -> List[str]
                - get_edge_score(node_a, node_b) -> float
              This adapter abstracts away differences between hypergraphs, HetNets, or entity graphs.

            tau (float): Pruning threshold in (0,1]. 
                        Paths with cumulative score < tau will be pruned (not expanded further).

            max_hops (int): Maximum number of edges (hops) along any path. 
                            Once a path reaches max_hops edges, it won't be expanded further.
        """
        self.adapter = graph_adapter
        self.tau = tau
        self.max_hops = max_hops

    def find_paths(
        self,
        start_node: str,
        end_node_type: Optional[str] = None,
        collect_all: bool = True
    ) -> List[Dict[str, Union[List[str], float]]]:
        """
        Perform a multi-hop traversal from `start_node` using a priority queue 
        to always expand the highest-scoring path first. 
        Each path's score is the product of edge scores (alpha*beta) along that path.

        Args:
            start_node (str): The node ID from which to begin traversal.
            end_node_type (str, optional): If provided, only paths ending in a node whose
                type == end_node_type are considered "valid" results. 
                If None, any node is considered a valid endpoint (if above threshold).
            collect_all (bool): If True, we collect all valid paths that meet or exceed `tau` 
                in their path score, up to `max_hops` edges. If False, you can stop 
                as soon as you find the first (or top) match (though the code as-is still 
                collects them all but you'd typically break after the first).

        Returns:
            A list of dictionaries in the form:
                [
                    {
                        "path": <List[str]>,   # node IDs from start_node to final node
                        "score": <float>       # cumulative path score
                    },
                    ...
                ]
            sorted by descending "score". Only includes paths whose score >= `tau`.

        Algorithm Steps:
          1. Initialize a priority queue (max-heap by storing negative scores).
          2. Start with path=[start_node], path_score=1.0, push (-1.0, [start_node]) into the queue.
          3. Pop the queue for the highest-scoring path so far:
             - If path_score >= tau and the last node matches `end_node_type` (or end_node_type is None),
               record it in results.
             - If path length < max_hops, expand neighbors:
               * For each neighbor, new_score = path_score * get_edge_score(current_node, neighbor).
               * If new_score >= tau, push new path into the queue.
          4. Sort final results in descending order by "score" and return them.

        Examples of Use:
            # Suppose 'hypergraph_adapter' wraps a hypergraph with alpha/beta in each edge.
            dmht = DynamicMultiHopTraversal(hypergraph_adapter, tau=0.05, max_hops=3)
            results = dmht.find_paths("DiseaseX", end_node_type="drug", collect_all=True)
        """

        # If the start_node is not valid, return empty
        if not self.adapter.is_valid_node(start_node):
            return []

        # Priority queue: (neg_score, path)
        pq = []
        # We begin with path_score = 1.0
        heappush(pq, (-1.0, [start_node]))

        visited_paths = set()  # optional: to prevent re-expanding the same path with identical score
        results = []

        while pq:
            neg_score, path = heappop(pq)
            path_score = -neg_score
            current_node = path[-1]

            # Check if path_score >= tau, meaning it's above the pruning threshold
            if path_score >= self.tau:
                # If there's an end_node_type, see if the last node's type matches
                node_type = self.adapter.get_node_type(current_node)
                if end_node_type is None or node_type == end_node_type:
                    # Record it in results
                    results.append({"path": path.copy(), "score": path_score})
                    if not collect_all:
                        # If we only wanted the first path, we could break here. 
                        # As is, we keep going for more.
                        pass

            # If we've reached max_hops edges, don't expand further
            if (len(path) - 1) >= self.max_hops:
                continue

            # Expand neighbors
            neighbors = self.adapter.get_neighbors(current_node)
            for nbr in neighbors:
                if nbr in path:
                    # skip cycles if we don't want them
                    continue
                edge_score = self.adapter.get_edge_score(current_node, nbr)
                new_score = path_score * edge_score
                # Prune if new_score < tau
                if new_score < self.tau:
                    continue

                new_path = path + [nbr]
                path_key = (tuple(new_path), round(new_score, 6))
                if path_key in visited_paths:
                    continue
                visited_paths.add(path_key)

                heappush(pq, (-new_score, new_path))

        # Sort results by descending score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    
class HypergraphAdapter:
    def __init__(self, hypergraph):
        self.hypergraph = hypergraph

    def is_valid_node(self, node_id: str) -> bool:
        return node_id in self.hypergraph.nodes

    def get_node_type(self, node_id: str) -> str:
        base_node = self.hypergraph.nodes.get(node_id)
        return base_node.node_type if base_node else ""

    def get_neighbors(self, node_id: str) -> List[str]:
        """
        Identify neighbors of node_id by scanning all edges (Simple, Directed, NodeDirected).
        """
        neighbors = set()
        for edge in self.hypergraph.edges.values():
            # We can retrieve alpha,beta from edge.metadata if needed
            if isinstance(edge, SimpleHyperedge) and node_id in edge.nodes:
                neighbors.update(edge.nodes)
            elif isinstance(edge, DirectedHyperedge):
                if node_id in edge.source_nodes:
                    neighbors.update(edge.target_nodes)
                elif node_id in edge.target_nodes:
                    neighbors.update(edge.source_nodes)
            elif isinstance(edge, NodeDirectedHyperedge):
                if node_id in edge.source_nodes:
                    neighbors.update(edge.target_nodes)
                elif node_id in edge.target_nodes:
                    neighbors.update(edge.source_nodes)
        neighbors.discard(node_id)  # remove self to avoid trivial loops
        return list(neighbors)

    def get_edge_score(self, node_a: str, node_b: str) -> float:
        """
        Return alpha*beta from edge.metadata["scores"]["alpha"], etc. 
        For hypergraphs, we might have multiple edges that connect node_a and node_b. 
        We could take the max or sum. Here, we do the max for demonstration.
        """
        best_score = 0.0
        for edge in self.hypergraph.edges.values():
            alpha = edge.metadata.get("scores", {}).get("alpha", 1.0)
            beta = edge.metadata.get("scores", {}).get("beta", 1.0)
            ab_score = alpha * beta

            if isinstance(edge, SimpleHyperedge):
                if node_a in edge.nodes and node_b in edge.nodes:
                    best_score = max(best_score, ab_score)

            elif isinstance(edge, DirectedHyperedge):
                # If node_a in source_nodes, node_b in target_nodes => valid
                if (node_a in edge.source_nodes and node_b in edge.target_nodes) or \
                   (node_b in edge.source_nodes and node_a in edge.target_nodes):
                    best_score = max(best_score, ab_score)

            elif isinstance(edge, NodeDirectedHyperedge):
                if (node_a in edge.source_nodes and node_b in edge.target_nodes) or \
                   (node_b in edge.source_nodes and node_a in edge.target_nodes):
                    best_score = max(best_score, ab_score)

        return best_score

class HetNetAdapter:
    def __init__(self, hetnet):
        self.hetnet = hetnet

    def is_valid_node(self, node_id: str) -> bool:
        return node_id in self.hetnet.nodes

    def get_node_type(self, node_id: str) -> str:
        return self.hetnet.nodes[node_id].node_type if node_id in self.hetnet.nodes else ""

    def get_neighbors(self, node_id: str) -> List[str]:
        """
        For each BaseEdge in hetnet.edges, if edge.source_id == node_id => neighbor = edge.target_id,
        or if edge.target_id == node_id => neighbor = edge.source_id
        """
        nbrs = set()
        for edge in self.hetnet.edges.values():
            if edge.source_id == node_id:
                nbrs.add(edge.target_id)
            elif edge.target_id == node_id:
                nbrs.add(edge.source_id)
        return list(nbrs)

    def get_edge_score(self, node_a: str, node_b: str) -> float:
        """
        We find the relevant BaseEdge (if any) connecting node_a and node_b.
        Then fetch alpha,beta from edge.metadata["scores"] as needed. 
        If multiple edges exist between the same pair, you can decide how to handle them. 
        For now, we return the max.
        """
        best_score = 0.0
        for edge in self.hetnet.edges.values():
            if (edge.source_id == node_a and edge.target_id == node_b) or \
               (edge.source_id == node_b and edge.target_id == node_a):
                alpha = edge.metadata.get("scores", {}).get("alpha", 1.0)
                beta = edge.metadata.get("scores", {}).get("beta", 1.0)
                ab_score = alpha * beta
                best_score = max(best_score, ab_score)
        return best_score

class EntitySpecificGraphAdapter:
    def __init__(self, entity_graph):
        self.entity_graph = entity_graph

    def is_valid_node(self, node_id: str) -> bool:
        return node_id in self.entity_graph.nodes

    def get_node_type(self, node_id: str) -> str:
        node_obj = self.entity_graph.nodes.get(node_id)
        # If you store node types in node_obj.attributes.get("node_type") or node_obj.metadata...
        return node_obj.attributes.get("node_type", "") if node_obj else ""

    def get_neighbors(self, node_id: str) -> List[str]:
        """
        For each EntityGraphEdge that references node_id in edge.connected_nodes,
        the neighbor is the other node(s) in connected_nodes.
        """
        nbrs = set()
        for edge in self.entity_graph.edges.values():
            if node_id in edge.connected_nodes:
                nbrs.update(edge.connected_nodes)
        nbrs.discard(node_id)
        return list(nbrs)

    def get_edge_score(self, node_a: str, node_b: str) -> float:
        """
        Check all edges that have [node_a, node_b] in connected_nodes.
        Retrieve alpha,beta from edge.metadata["scores"] if present. 
        We'll again return max if multiple edges exist.
        """
        best_score = 0.0
        for edge in self.entity_graph.edges.values():
            if node_a in edge.connected_nodes and node_b in edge.connected_nodes:
                alpha = edge.metadata.get("scores", {}).get("alpha", 1.0)
                beta = edge.metadata.get("scores", {}).get("beta", 1.0)
                ab_score = alpha * beta
                best_score = max(best_score, ab_score)
        return best_score
