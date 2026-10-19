"""Serializer for real-valued vector candidates used by the synthetic numeric tasks."""

import json

from scileo_agent.core.data_models import Candidate
from scileo_agent.core.registry.serializer_registry import Serializer, register_serializer_class


@register_serializer_class(
    name="vector_serializer",
    description="Serializes real-valued vector candidates (list of floats in [0, 1]) to a JSON string",
)
class VectorSerializer(Serializer):
    @property
    def sample_schema(self) -> str:
        return "str"

    @property
    def sample_description(self) -> str:
        return "a JSON array of floats in [0, 1] (the design parameter vector)"

    def serialize(self, candidate: Candidate) -> str:
        return json.dumps([round(float(v), 6) for v in candidate.representation])

    def deserialize(self, data: str) -> Candidate:
        return Candidate(representation=[float(v) for v in json.loads(data)])
