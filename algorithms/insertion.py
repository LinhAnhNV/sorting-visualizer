"""Insertion Sort (dạng hoán đổi liền kề để dễ quan sát)."""
from __future__ import annotations

from typing import Iterator

from .base import SortingAlgorithm, Step


class InsertionSort(SortingAlgorithm):
    key = "insertion"
    name = "Insertion Sort"
    description = ("Xem phần đầu dãy là đã sắp xếp; lấy lần lượt từng phần tử tiếp theo và "
                   "chèn vào đúng chỗ bằng cách đổi chỗ lùi dần. Rất nhanh với dãy gần như đã sắp xếp.")
    time_best = "O(n)"
    time_average = "O(n²)"
    time_worst = "O(n²)"
    space = "O(1)"
    stable = True

    def _steps(self) -> Iterator[Step]:
        a = self.data
        for i in range(1, len(a)):
            j = i
            while j > 0:
                yield self._cmp(j - 1, j)
                if a[j - 1] > a[j]:
                    yield self._swap(j - 1, j)
                    j -= 1
                else:
                    break
