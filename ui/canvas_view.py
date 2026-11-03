"""Canvas vẽ dãy số dưới dạng các cột và chú giải màu."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Sequence

from algorithms.base import Step, StepType

BG_COLOR = "#1e1f26"
BASE_COLOR = "#6c8ebf"
COLORS = {
    StepType.COMPARE: "#f4c20d",    # vàng
    StepType.SWAP: "#e74c3c",       # đỏ
    StepType.OVERWRITE: "#e67e22",  # cam
    StepType.PIVOT: "#9b59b6",      # tím
    StepType.DONE: "#2ecc71",       # xanh lá
}
LEGEND = [
    (BASE_COLOR, "Bình thường"),
    (COLORS[StepType.COMPARE], "Đang so sánh"),
    (COLORS[StepType.SWAP], "Hoán đổi"),
    (COLORS[StepType.OVERWRITE], "Ghi đè"),
    (COLORS[StepType.PIVOT], "Phần tử chốt"),
    (COLORS[StepType.DONE], "Đã xong"),
]

PAD = 10
LABEL_MAX_BARS = 40   # chỉ hiện số trên đầu cột khi có ít cột


class CanvasView(tk.Canvas):
    """Vẽ các cột. Các item của Canvas được tạo một lần rồi chỉ cập nhật phần thay đổi,
    nhờ đó hoạt hình vẫn mượt với vài trăm cột."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg", BG_COLOR)
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        self._vals: List[int] = []
        self._cols: List[str] = []
        self._bars: List[int] = []
        self._texts: List[int] = []
        self._lo = 0
        self._hi = 1
        self._size = (0, 0)
        self.bind("<Configure>", self._on_resize)

    # ---- API công khai ---------------------------------------------------
    def set_data(self, data: Sequence[int]) -> None:
        """Nạp dãy mới (đặt lại màu, tính lại thang chiều cao)."""
        self._vals = list(data)
        self._cols = [BASE_COLOR] * len(self._vals)
        if self._vals:
            self._lo, self._hi = min(self._vals), max(self._vals)
        self._rebuild()

    def render(self, data: Sequence[int], step: Optional[Step] = None) -> None:
        """Cập nhật theo trạng thái dãy hiện tại và bước vừa thực hiện."""
        n = len(data)
        if n != len(self._vals):
            self.set_data(data)
        highlight = {}
        all_done = False
        if step is not None:
            if step.type is StepType.DONE:
                all_done = True
            else:
                color = COLORS[step.type]
                for idx in step.indices:
                    highlight[idx] = color

        for i in range(n):
            color = COLORS[StepType.DONE] if all_done else highlight.get(i, BASE_COLOR)
            if data[i] != self._vals[i]:
                self._vals[i] = data[i]
                self._place_bar(i)
            if color != self._cols[i]:
                self._cols[i] = color
                if i < len(self._bars):
                    self.itemconfig(self._bars[i], fill=color)

    # ---- Nội bộ ----------------------------------------------------------
    def _on_resize(self, event) -> None:
        if (event.width, event.height) != self._size:
            self._size = (event.width, event.height)
            self._rebuild()

    def _dims(self):
        w = max(self.winfo_width(), 100)
        h = max(self.winfo_height(), 100)
        return w, h

    def _bar_height(self, value: int, usable: float) -> float:
        if self._hi > self._lo:
            frac = 0.05 + 0.95 * (value - self._lo) / (self._hi - self._lo)
        else:
            frac = 0.5
        return usable * min(1.0, max(0.0, frac))

    def _rebuild(self) -> None:
        self.delete("all")
        self._bars = []
        self._texts = []
        n = len(self._vals)
        if n == 0:
            return
        show_labels = n <= LABEL_MAX_BARS
        for i in range(n):
            self._bars.append(self.create_rectangle(0, 0, 0, 0, width=0, fill=self._cols[i]))
            if show_labels:
                self._texts.append(self.create_text(
                    0, 0, text=str(self._vals[i]), fill="#cfd3dc", font=("TkDefaultFont", 9)))
        for i in range(n):
            self._place_bar(i)

    def _place_bar(self, i: int) -> None:
        if i >= len(self._bars):
            return
        w, h = self._dims()
        n = len(self._vals)
        bar_w = (w - 2 * PAD) / n
        gap = 1 if bar_w >= 4 else 0
        label_room = 16 if self._texts else 0
        usable = h - 2 * PAD - label_room
        bh = self._bar_height(self._vals[i], usable)
        x0 = PAD + i * bar_w + gap / 2
        x1 = PAD + (i + 1) * bar_w - gap / 2
        y1 = h - PAD
        y0 = y1 - bh
        self.coords(self._bars[i], x0, y0, x1, y1)
        if self._texts:
            self.coords(self._texts[i], (x0 + x1) / 2, y0 - 8)
            self.itemconfig(self._texts[i], text=str(self._vals[i]))


class ColorLegend(ttk.Frame):
    """Hàng chú giải màu nằm dưới Canvas."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        for color, text in LEGEND:
            swatch = tk.Frame(self, width=14, height=14, bg=color)
            swatch.pack(side="left", padx=(10, 3), pady=4)
            ttk.Label(self, text=text).pack(side="left")
