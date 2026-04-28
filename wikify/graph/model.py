from dataclasses import dataclass, field


@dataclass(frozen=True)
class GraphNode:
    id: str
    path: str
    relative_path: str
    type: str
    title: str
    label: str
    tags: list[str] = field(default_factory=list)
    degree: int = 0

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'path': self.path,
            'relative_path': self.relative_path,
            'type': self.type,
            'title': self.title,
            'label': self.label,
            'tags': list(self.tags),
            'degree': self.degree,
        }


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    type: str
    provenance: str
    confidence: float
    source_path: str
    line: int
    label: str

    def to_dict(self) -> dict:
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'provenance': self.provenance,
            'confidence': self.confidence,
            'source_path': self.source_path,
            'line': self.line,
            'label': self.label,
        }
