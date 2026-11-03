"""Điều khiển trạng thái chạy của một thuật toán (không phụ thuộc Tkinter).

Máy trạng thái:

    IDLE --start--> RUNNING <--pause/resume--> PAUSED
      |                |                          |
      +-----step-------+---------> FINISHED <-----+
    (reset đưa mọi trạng thái về IDLE)
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from algorithms.base import SortingAlgorithm, Step, StepType


class RunState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


def speed_to_timing(speed: int) -> Tuple[int, int]:
    """Đổi giá trị slider (1..100) thành (độ trễ ms giữa hai tick, số bước mỗi tick).

    Tốc độ thấp: 1 bước/tick, tick thưa. Tốc độ cao: tick dày và nhiều bước/tick
    để dãy lớn vẫn chạy xong trong thời gian hợp lý.
    """
    s = max(1, min(100, int(speed)))
    delay = max(10, round(1000 / s))
    steps = 1 + (s - 1) // 10
    return delay, steps


class SortRunner:
    """Giữ thuật toán hiện tại và trạng thái RUNNING/PAUSED/..."""

    def __init__(self) -> None:
        self.algorithm: Optional[SortingAlgorithm] = None
        self.state: RunState = RunState.IDLE
        self.last_step: Optional[Step] = None

    # ---- nạp / đặt lại ---------------------------------------------------
    def load(self, algorithm: SortingAlgorithm) -> None:
        self.algorithm = algorithm
        self.state = RunState.IDLE
        self.last_step = None

    def reset(self) -> None:
        if self.algorithm is not None:
            self.algorithm.reset()
        self.state = RunState.IDLE
        self.last_step = None

    # ---- chuyển trạng thái (trả về True nếu hợp lệ) ----------------------
    def start(self) -> bool:
        if self.algorithm is None or self.state is not RunState.IDLE:
            return False
        self.state = RunState.RUNNING
        return True

    def pause(self) -> bool:
        if self.state is not RunState.RUNNING:
            return False
        self.state = RunState.PAUSED
        return True

    def resume(self) -> bool:
        if self.state is not RunState.PAUSED:
            return False
        self.state = RunState.RUNNING
        return True

    # ---- tiến bước -------------------------------------------------------
    def step_once(self) -> Optional[Step]:
        """Chạy đúng một bước thủ công (chỉ khi IDLE hoặc PAUSED)."""
        if self.algorithm is None or self.state not in (RunState.IDLE, RunState.PAUSED):
            return None
        step = self._advance()
        if step is not None and self.state is not RunState.FINISHED:
            self.state = RunState.PAUSED
        return step

    def tick(self, count: int = 1) -> Optional[Step]:
        """Chạy ``count`` bước liên tiếp khi đang RUNNING; trả về bước cuối cùng."""
        if self.algorithm is None or self.state is not RunState.RUNNING:
            return None
        last = None
        for _ in range(max(1, count)):
            step = self._advance()
            if step is None:
                break
            last = step
            if step.type is StepType.DONE:
                break
        return last

    def _advance(self) -> Optional[Step]:
        step = self.algorithm.step()
        if step is None:
            self.state = RunState.FINISHED
            return None
        self.last_step = step
        if step.type is StepType.DONE:
            self.state = RunState.FINISHED
        return step

    @property
    def is_running(self) -> bool:
        return self.state is RunState.RUNNING
