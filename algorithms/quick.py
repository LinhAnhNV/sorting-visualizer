"""Quick Sort (Lomuto, chốt là phần tử cuối, dùng ngăn xếp thay cho đệ quy)."""
from __future__ import annotations

from typing import Iterator

from .base import SortingAlgorithm, Step


class QuickSort(SortingAlgorithm):
    key = "quick"
    name = "Quick Sort"
    description = ("Chọn phần tử cuối làm chốt (pivot), phân hoạch dãy thành phần nhỏ hơn và "
                   "lớn hơn chốt rồi xử lý từng phần. Dùng ngăn xếp tường minh nên không bị giới "
                   "hạn đệ quy; trường hợp xấu (dãy đã sắp xếp) rơi vào O(n²).")
    time_best = "O(n log n)"
    time_average = "O(n log n)"
    time_worst = "O(n²)"
    space = "O(log n)"
    stable = False

    def _steps(self) -> Iterator[Step]:
        a = self.data
        stack = [(0, len(a) - 1)]
        while stack:
            lo, hi = stack.pop()
            if lo >= hi:
                continue
            yield self._pivot(hi)
            pivot = a[hi]
            i = lo
            for j in range(lo, hi):
                yield self._cmp(j, hi)
                if a[j] < pivot:
                    if i != j:
                        yield self._swap(i, j)
                    i += 1
            if i != hi:
                yield self._swap(i, hi)
            stack.append((lo, i - 1))
            stack.append((i + 1, hi))
