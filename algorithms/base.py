"""Lớp trừu tượng SortingAlgorithm và các kiểu dữ liệu mô tả một "bước" sắp xếp.

Ý tưởng cốt lõi
---------------
Mỗi thuật toán được viết dưới dạng *generator* (``_steps``). Mỗi lần ``yield``
là một bước nhỏ (so sánh / hoán đổi / ghi đè ...). Giao diện chỉ việc gọi
``step()`` mỗi lần cần tiến thêm một bước, còn benchmark gọi ``run_all()``.
Lớp này hoàn toàn không biết Tkinter tồn tại nên có thể kiểm thử độc lập.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Iterator, List, NamedTuple, Optional, Sequence, Tuple


class StepType(Enum):
    """Loại thao tác của một bước."""

    COMPARE = "compare"      # so sánh hai phần tử
    SWAP = "swap"            # hoán đổi hai phần tử
    OVERWRITE = "overwrite"  # ghi đè một vị trí (merge sort)
    PIVOT = "pivot"          # đánh dấu phần tử chốt (quick sort)
    DONE = "done"            # thuật toán kết thúc


class Step(NamedTuple):
    """Một bước thực thi: loại thao tác và các chỉ số cột liên quan."""

    type: StepType
    indices: Tuple[int, ...]


class SortingAlgorithm(ABC):
    """Lớp cha của mọi thuật toán sắp xếp.

    Lớp con chỉ cần:
      * khai báo các thuộc tính mô tả (``name``, ``key``, độ phức tạp ...),
      * cài đặt generator ``_steps()``; dùng ``_cmp``, ``_swap``, ``_write``,
        ``_pivot`` để vừa thực hiện thao tác, vừa cập nhật bộ đếm, vừa tạo Step.
    """

    # ---- Thông tin mô tả (lớp con ghi đè) -------------------------------
    key: str = "base"
    name: str = "Base"
    description: str = ""
    time_best: str = ""
    time_average: str = ""
    time_worst: str = ""
    space: str = ""
    stable: bool = False

    def __init__(self, data: Sequence[int]):
        self.original: List[int] = list(data)
        self.reset()

    # ---- Vòng đời --------------------------------------------------------
    def reset(self) -> None:
        """Đưa thuật toán về trạng thái ban đầu với dãy dữ liệu gốc."""
        self.data: List[int] = list(self.original)
        self.comparisons = 0
        self.swaps = 0
        self.overwrites = 0
        self.steps_count = 0
        self.finished = False
        self._gen: Iterator[Step] = self._steps()

    @abstractmethod
    def _steps(self) -> Iterator[Step]:
        """Generator mô tả thuật toán. Mỗi ``yield`` là một bước."""

    # ---- Giao diện sử dụng -----------------------------------------------
    def step(self) -> Optional[Step]:
        """Chạy một bước.

        Trả về ``Step`` kế tiếp. Khi thuật toán vừa xong sẽ trả về một Step
        loại ``DONE`` đúng một lần; các lần gọi sau trả về ``None``.
        """
        if self.finished:
            return None
        try:
            s = next(self._gen)
        except StopIteration:
            self.finished = True
            return Step(StepType.DONE, ())
        self.steps_count += 1
        return s

    def run_all(self) -> None:
        """Chạy một mạch đến hết (dùng cho benchmark / kiểm thử, không cần UI)."""
        while self.step() is not None:
            pass

    def is_sorted(self) -> bool:
        a = self.data
        return all(a[i] <= a[i + 1] for i in range(len(a) - 1))

    def info(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "best": self.time_best,
            "average": self.time_average,
            "worst": self.time_worst,
            "space": self.space,
            "stable": self.stable,
        }

    # ---- Trợ giúp cho lớp con --------------------------------------------
    def _cmp(self, i: int, j: int) -> Step:
        """Ghi nhận một lần so sánh giữa chỉ số i và j."""
        self.comparisons += 1
        return Step(StepType.COMPARE, (i, j))

    def _swap(self, i: int, j: int) -> Step:
        """Hoán đổi a[i] và a[j], ghi nhận một lần hoán đổi."""
        a = self.data
        a[i], a[j] = a[j], a[i]
        self.swaps += 1
        return Step(StepType.SWAP, (i, j))

    def _write(self, k: int, value: int) -> Step:
        """Ghi đè a[k] = value, ghi nhận một lần ghi đè."""
        self.data[k] = value
        self.overwrites += 1
        return Step(StepType.OVERWRITE, (k,))

    def _pivot(self, i: int) -> Step:
        """Đánh dấu phần tử chốt (không tính vào so sánh/hoán đổi)."""
        return Step(StepType.PIVOT, (i,))

    def __repr__(self) -> str:  # pragma: no cover - chỉ để debug
        return f"<{self.__class__.__name__} n={len(self.original)}>"
