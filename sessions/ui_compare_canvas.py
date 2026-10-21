import math
import tkinter as tk
from tkinter import ttk

import stats

# Mỗi cột trong biểu đồ: (nhãn, khóa trong stats.by_algorithm, màu)
SERIES = (
    ("Swaps trung bình", "avg_swaps", "#4C78A8"),
    ("So sánh trung bình", "avg_comparisons", "#F58518"),
)
TEXT_COLOR = "#333333"
MUTED_COLOR = "#777777"
GRID_COLOR = "#DDDDDD"


def _nice_step(raw):
    """Làm tròn bước chia trục Y về dạng 1, 2, 2.5, 5 x 10^k."""
    if raw <= 0:
        return 1
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude


def draw_comparison_chart(canvas, data, width, height):
    """Vẽ biểu đồ cột nhóm so sánh các thuật toán lên canvas.
    data: kết quả của stats.by_algorithm(sessions)."""
    canvas.delete("all")
    if not data:
        canvas.create_text(width / 2, height / 2, text="Chưa có dữ liệu để so sánh",
                           fill=TEXT_COLOR, font=("TkDefaultFont", 12))
        return

    left, right, top, bottom = 60, 20, 60, 70
    plot_w = max(width - left - right, 50)
    plot_h = max(height - top - bottom, 50)
    x0, y0 = left, top + plot_h  # góc dưới bên trái của vùng vẽ

    names = sorted(data)
    max_val = max(data[n][key] for n in names for _, key, _ in SERIES)
    step = _nice_step(max_val / 5) if max_val > 0 else 1
    ticks = max(1, math.ceil(max_val / step))
    y_max = step * ticks

    def y_of(value):
        return y0 - value / y_max * plot_h

    # Lưới ngang + nhãn trục Y
    for i in range(ticks + 1):
        value = step * i
        y = y_of(value)
        canvas.create_line(x0, y, x0 + plot_w, y, fill=GRID_COLOR)
        canvas.create_text(x0 - 8, y, text=f"{value:g}", anchor="e", fill=TEXT_COLOR)
    canvas.create_line(x0, top, x0, y0, fill=TEXT_COLOR)
    canvas.create_line(x0, y0, x0 + plot_w, y0, fill=TEXT_COLOR)

    # Các cột
    group_w = plot_w / len(names)
    bar_w = min(group_w * 0.3, 60)
    for gi, name in enumerate(names):
        cx = x0 + group_w * (gi + 0.5)
        stat = data[name]
        for si, (_label, key, color) in enumerate(SERIES):
            value = stat[key]
            bx0 = cx - bar_w + si * bar_w
            bx1 = bx0 + bar_w
            by = y_of(value)
            canvas.create_rectangle(bx0, by, bx1, y0, fill=color, outline="")
            canvas.create_text((bx0 + bx1) / 2, by - 8, text=f"{value:g}", fill=TEXT_COLOR)
        canvas.create_text(cx, y0 + 16, text=name, fill=TEXT_COLOR,
                           font=("TkDefaultFont", 10, "bold"))
        canvas.create_text(cx, y0 + 34, fill=MUTED_COLOR,
                           text=f"{stat['count']} session, TB {stat['avg_size']:g} phần tử")

    # Chú thích
    lx = x0
    for label, _key, color in SERIES:
        canvas.create_rectangle(lx, 20, lx + 12, 32, fill=color, outline="")
        canvas.create_text(lx + 18, 26, text=label, anchor="w", fill=TEXT_COLOR)
        lx += 170


class CompareWindow(tk.Toplevel):
    """Cửa sổ canvas so sánh hiệu năng các thuật toán.
    get_sessions: hàm trả về (danh sách session, mô tả phạm vi)."""

    def __init__(self, master, get_sessions):
        super().__init__(master)
        self.title("So sánh hiệu năng thuật toán")
        self.geometry("740x480")
        self.get_sessions = get_sessions

        top = ttk.Frame(self, padding=(8, 8, 8, 0))
        top.pack(fill="x")
        self.info = ttk.Label(top)
        self.info.pack(side="left")
        ttk.Button(top, text="Làm mới", command=self.redraw).pack(side="right")

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda _e: self.redraw())  # vẽ lại khi đổi kích thước

        ttk.Label(self, foreground="gray", wraplength=700,
                  text="Hiệu năng tính bằng số lần swap và so sánh (càng thấp càng tốt). "
                       "Kích thước dãy số mỗi thuật toán có thể khác nhau, xem dòng phần tử trung bình bên dưới tên."
                  ).pack(fill="x", padx=8, pady=(0, 8))

    def redraw(self):
        sessions, scope = self.get_sessions()
        self.info.config(text=f"Phạm vi: {scope} | {len(sessions)} session")
        draw_comparison_chart(self.canvas, stats.by_algorithm(sessions),
                              self.canvas.winfo_width(), self.canvas.winfo_height())