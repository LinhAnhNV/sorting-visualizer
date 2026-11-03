"""Gói các thuật toán sắp xếp và bộ đăng ký (registry)."""
from __future__ import annotations

from typing import Dict, List, Sequence, Type

from .base import SortingAlgorithm, Step, StepType
from .bubble import BubbleSort
from .insertion import InsertionSort
from .merge import MergeSort
from .quick import QuickSort
from .selection import SelectionSort

ALGORITHM_CLASSES: List[Type[SortingAlgorithm]] = [
    BubbleSort, SelectionSort, InsertionSort, MergeSort, QuickSort,
]

ALGORITHMS: Dict[str, Type[SortingAlgorithm]] = {cls.name: cls for cls in ALGORITHM_CLASSES}
_BY_KEY: Dict[str, Type[SortingAlgorithm]] = {cls.key: cls for cls in ALGORITHM_CLASSES}


def algorithm_names() -> List[str]:
    return [cls.name for cls in ALGORITHM_CLASSES]


def get_class(name_or_key: str) -> Type[SortingAlgorithm]:
    """Tìm lớp thuật toán theo tên hiển thị hoặc khoá ngắn (không phân biệt hoa thường)."""
    token = name_or_key.strip().lower()
    for cls in ALGORITHM_CLASSES:
        if token in (cls.name.lower(), cls.key):
            return cls
    raise KeyError(f"Không có thuật toán '{name_or_key}'")


def create(name_or_key: str, data: Sequence[int]) -> SortingAlgorithm:
    return get_class(name_or_key)(data)


__all__ = [
    "SortingAlgorithm", "Step", "StepType",
    "BubbleSort", "SelectionSort", "InsertionSort", "MergeSort", "QuickSort",
    "ALGORITHM_CLASSES", "ALGORITHMS", "algorithm_names", "get_class", "create",
]
