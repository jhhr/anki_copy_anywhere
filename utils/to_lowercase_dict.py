from typing import Any, Dict, Iterable, Protocol, Tuple, Union


# Type that'll match anki's Note class
class DictLike(Protocol):
    def items(self) -> Iterable[Tuple[str, Any]]: ...
    def keys(self) -> Iterable[str]: ...
    def values(self) -> Iterable[Any]: ...


def to_lowercase_dict(d: Union[Dict[str, Any], DictLike, None]) -> Dict[str, Any]:
    """Converts a dictionary to lowercase keys"""
    if d is None:
        return {}
    return {k.lower(): v for k, v in d.items()}
