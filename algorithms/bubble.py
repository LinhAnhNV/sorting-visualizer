"""Bubble Sort (có cờ dừng sớm)."""
from __future__ import annotations

from typing import Iterator

from .base import SortingAlgorithm, Step


class BubbleSort(SortingAlgorithm):
    key = "bubble"
    name = "Bubble Sort"
    description = ("Lần lượt so sánh các cặp phần tử liền kề và đổi chỗ nếu sai thứ tự; "
                   "phần tử lớn nhất 'nổi' dần về cuối. Dừng sớm nếu một lượt không có hoán đổi.")
    time_best = "O(n)"
    time_average = "O(n²)"
    time_worst = "O(n²)"
    space = "O(1)"
    stable = True

    def _steps(self) -> Iterator[Step]:
        a = self.data
        n = len(a)
        for i in range(n - 1):
            swapped = False
            for j in range(n - 1 - i):
                yield self._cmp(j, j + 1)
                if a[j] > a[j + 1]:
                    yield self._swap(j, j + 1)
                    swapped = True
            if not swapped:
                break
