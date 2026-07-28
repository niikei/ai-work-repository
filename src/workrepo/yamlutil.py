"""Strict YAML loading shared by schemas, policy, and frontmatter."""

from collections.abc import Hashable

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: StrictSafeLoader,
    node: MappingNode,
    deep: bool = False,  # noqa: FBT001, FBT002
) -> dict[Hashable, object]:
    loader.flatten_mapping(node)
    mapping: dict[Hashable, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, Hashable):
            context = "while constructing a mapping"
            problem = "found an unhashable key"
            raise ConstructorError(
                context,
                node.start_mark,
                problem,
                key_node.start_mark,
            )
        if key in mapping:
            context = "while constructing a mapping"
            problem = f"found duplicate key {key!r}"
            raise ConstructorError(
                context,
                node.start_mark,
                problem,
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_yaml(source: str) -> object:
    """Load YAML safely and reject duplicate keys."""
    return yaml.load(source, Loader=StrictSafeLoader)  # noqa: S506
