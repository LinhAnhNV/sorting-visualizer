"""Merge Sort (chia để trị, dùng bước GHI ĐÈ thay vì hoán đổi)."""
from __future__ import annotations

from typing import Iterator

from .base import SortingAlgorithm, Step


class MergeSort(SortingAlgorithm):
    key = "merge"
    name = "Merge Sort"
    description = ("Chia đôi dãy, sắp xếp đệ quy từng nửa rồi trộn hai nửa đã sắp xếp. "
                   "Không hoán đổi mà ghi đè giá trị từ mảng phụ nên thống kê dùng 'ghi đè'.")
    time_best = "O(n log n)"
    time_average = "O(n log n)"
    time_worst = "O(n log n)"
    space = "O(n)"
    stable = True

    def _steps(self) -> Iterator[Step]:
        yield from self._sort(0, len(self.data) - 1)

    def _sort(self, lo: int, hi: int) -> Iterator[Step]:
        if lo >= hi:
            return
        mid = (lo + hi) // 2
        yield from self._sort(lo, mid)
        yield from self._sort(mid + 1, hi)
        yield from self._merge(lo, mid, hi)

    def _merge(self, lo: int, mid: int, hi: int) -> Iterator[Step]:
        a = self.data
        left = a[lo:mid + 1]
        right = a[mid + 1:hi + 1]
        i = j = 0
        k = lo
        while i < len(left) and j < len(right):
            yield self._cmp(lo + i, mid + 1 + j)
            if left[i] <= right[j]:
                yield self._write(k, left[i])
                i += 1
            else:
                yield self._write(k, right[j])
                j += 1
            k += 1
        while i < len(left):
            yield self._write(k, left[i])
            i += 1
            k += 1
        while j < len(right):
            yield self._write(k, right[j])
            j += 1
            k += 1
