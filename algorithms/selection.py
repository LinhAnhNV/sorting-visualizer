"""Selection Sort."""
from __future__ import annotations

from typing import Iterator

from .base import SortingAlgorithm, Step


class SelectionSort(SortingAlgorithm):
    key = "selection"
    name = "Selection Sort"
    description = ("Mỗi lượt tìm phần tử nhỏ nhất trong phần chưa sắp xếp rồi đổi chỗ "
                   "về đầu phần đó. Số hoán đổi rất ít (tối đa n-1).")
    time_best = "O(n²)"
    time_average = "O(n²)"
    time_worst = "O(n²)"
    space = "O(1)"
    stable = False

    def _steps(self) -> Iterator[Step]:
        a = self.data
        n = len(a)
        for i in range(n - 1):
            m = i
            for j in range(i + 1, n):
                yield self._cmp(m, j)
                if a[j] < a[m]:
                    m = j
            if m != i:
                yield self._swap(i, m)
