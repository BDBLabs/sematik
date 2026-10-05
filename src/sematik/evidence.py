"""Semantic Evidence Graph — durable reasons behind mappings (spec §6)."""

from __future__ import annotations

from dataclasses import dataclass, field


class EdgeRel:
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVES_FROM = "derives-from"
    MAPS_TO = "maps-to"
    SUPERSEDES = "supersedes"
    ALIASES = "aliases"
    REPRESENTS = "represents"
    CALCULATED_BY = "calculated-by"
    POPULATED_BY = "populated-by"
    DISPLAYED_BY = "displayed-by"
    REPORTED_AS = "reported-as"
    GOVERNED_BY = "governed-by"
    VALID_DURING = "valid-during"
    TRANSFORMED_BY = "transformed-by"
    RECONCILED_WITH = "reconciled-with"


@dataclass
class Edge:
    src: str
    dst: str
    rel: str


@dataclass
class EvidenceGraph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node_id: str, kind: str, **attrs) -> None:
        self.nodes[node_id] = {"kind": kind, **attrs}

    def link(self, src: str, rel: str, dst: str) -> None:
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError("both endpoints must exist before linking")
        self.edges.append(Edge(src, dst, rel))

    def why(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.dst == node_id or e.src == node_id]

    def path_summary(self, node_id: str) -> list[str]:
        """BFS outward listing reason chains touching this node."""
        seen, out = set(), []
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for e in self.edges:
                if e.src == cur and e.dst not in seen:
                    out.append(f"{cur} -[{e.rel}]-> {e.dst}")
                    seen.add(e.dst)
                    stack.append(e.dst)
        return out

    def to_json(self) -> str:
        import json
        return json.dumps(
            {"nodes": self.nodes, "edges": [vars(e) for e in self.edges]},
            sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, payload: str) -> "EvidenceGraph":
        import json
        raw = json.loads(payload)
        g = cls(nodes=raw["nodes"])
        g.edges = [Edge(**e) for e in raw["edges"]]
        return g
