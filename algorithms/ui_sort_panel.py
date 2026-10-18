"""Giao diện mô phỏng thuật toán sắp xếp.

SortPanel:    nhập/sinh dãy số, chọn thuật toán, vẽ cột trên Canvas, chạy từng bước.
ControlPanel: hàng nút Start/Pause/Step/Reset và thanh tốc độ (Custom Widget).

Chạy thử riêng (từ thư mục gốc dự án):  python -m algorithms.ui_sort_panel"""

import random
import time

import config
from accounts.validators import parse_number_list

import tkinter as tk
from tkinter import messagebox ,ttk
import config
from algorithms.benchmark import ALGORITHMS

class ControlPanel(tk.Frame):
    """Hàng nút điều khiển và thanh trượt tốc độ.
 
    Panel không tự chạy thuật toán: nó chỉ gọi các hàm do nơi sử
    dụng truyền vào, nên đặt vào cửa sổ nào cũng dùng được."""
    def __init__(self, parent, on_start, on_pause, on_step, on_reset):
        super().__init__(parent)
        buttons = (
            ("Start", on_start),
            ("Pause", on_pause),
            ("Step", on_step),
            ("Reset", on_reset),
        )
        """Trong Frame này chỉ dùng grid (không trộn với pack)"""
        for col, (text, command) in enumerate(buttons):
            tk.Button(self, text=text, width=8, command=command).grid(row=0, column=col, padx=3)
            self.columnconfigure(col, weight=1)

        self.speed = tk.IntVar(value=config.DEFAULT_SPEED)
        tk.Scale(
            self, from_=1, to=10, orient="horizontal", label="Tốc độ", variable=self.speed
        ).grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))

    def get_delay(self):
        """Thời gian chờ giữa hai bước (ms): tốc độ càng cao càng ngắn."""
        return 600 - self.speed.get() * 50

class SortPanel(tk.Frame):
    """Khung mô phỏng: một thuật toán chạy từng bước, vẽ trên Canvas.
 
    on_finish: hàm nhận dict kết quả khi người dùng bấm "Lưu phiên" sau khi
    chạy xong, dạng {"algorithm", "values", "comparisons", "swaps", "time_ms"}."""
    
    def __init__(self, parent, on_finish=None):
        super().__init__(parent)
        self.on_finish = on_finish

        # Tên thuật toán -> lớp. Lấy từ danh sách ALGORITHMS trong benchmark.py
        # để thêm thuật toán mới chỉ phải sửa một chỗ.
        self.algorithms = {cls([]).get_name(): cls for cls in ALGORITHMS}

        self.base_values = []   # dãy gốc: dùng cho Reset và Lưu phiên
        self.algo = None        # thuật toán đang chạy
        self.highlight = ()     # cặp cột vừa so sánh
        self.after_id = None    # mã của lệnh .after() đang chờ
        self.running = False
        self.saved = False      # lần chạy này đã lưu chưa

        self._build_widgets()
        self.load_random()

    # ---------- dựng giao diện ----------
    def _build_widgets(self):
        """Hàng nhập liệu: bên trong chỉ dùng grid"""
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        top.columnconfigure(1, weight=1)

        tk.Label(top, text="Dãy số:").grid(row=0, column=0, sticky="w")
        self.entry = tk.Entry(top)
        self.entry.grid(row=0, column=1, sticky="ew", padx=4)
        self.entry.bind("<Return>", lambda event: self.apply_input())
        tk.Button(top, text="Áp dụng", command=self.apply_input).grid(row=0, column=2)
        tk.Button(top, text="Random", command=self.load_random).grid(row=0, column=3, padx=(4, 0))

        tk.Label(top, text="Thuật toán:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.combo = ttk.Combobox(top, values=list(self.algorithms), state="readonly", width=18)
        self.combo.current(0)
        self.combo.grid(row=1, column=1, sticky="w", padx=4, pady=(6, 0))
        self.combo.bind("<<ComboboxSelected>>", lambda event: self.on_algorithm_changed())

        # Các thành phần còn lại là con trực tiếp của SortPanel: chỉ dùng pack
        self.canvas = tk.Canvas(
            self, width=config.CANVAS_WIDTH, height=config.CANVAS_HEIGHT, bg=config.CANVAS_BG
        )
        self.canvas.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas.bind("<Configure>", lambda event: self.draw())  # cửa sổ co giãn thì vẽ lại

        self.counts_label = tk.Label(self, text="")
        self.counts_label.pack(pady=2)

        self.controls = ControlPanel(
            self,
            on_start=self.start,
            on_pause=self.pause,
            on_step=self.step_button,
            on_reset=self.reset,
        )
        self.controls.pack(fill="x", padx=8, pady=4)

        tk.Button(self, text="Lưu phiên", command=self.save_session).pack(pady=(2, 8))

    # ---------- nhập dãy số ----------
    def parse_values(self, text):
        """Đổi chuỗi "5, 3, 8" thành list số nguyên dương. Sai thì báo ValueError."""
        values = parse_number_list(text)
        if len(values) > config.MAX_ELEMENTS:
            raise ValueError(f"Tối đa {config.MAX_ELEMENTS} phần tử, bạn nhập {len(values)}.")
        return values

    def apply_input(self):
        try:
            values = self.parse_values(self.entry.get())

        except ValueError as err:
            messagebox.showerror("Dãy số không hợp lệ", str(err))
            return
        self.set_values(values)

    def load_random(self):
        values = [
            random.randint(config.RANDOM_MIN, config.RANDOM_MAX)
            for _ in range(config.RANDOM_SIZE)
        ]
        self.set_values(values)

    def set_values(self, values):
        """Nạp dãy mới: dừng chạy, tạo lại thuật toán, vẽ lại."""
        self.pause()
        self.base_values = list(values)
        self.entry.delete(0, "end")
        self.entry.insert(0, ", ".join(str(v) for v in values))
        self.new_algo()
        self.draw()

    def new_algo(self):
        self.algo = self.algorithms[self.combo.get()](self.base_values)
        self.highlight = ()
        self.saved = False

    def on_algorithm_changed(self):
        self.pause()
        self.new_algo()
        self.draw()

    # ---------- vẽ ----------
    def _bar_color(self, index):
        if self.algo.is_done():
            return config.COLOR_DONE
        if index in self.highlight:
            return config.COLOR_COMPARE
        return config.COLOR_BAR

    def draw(self):
        self.canvas.delete("all")
        values = self.algo.get_state()
        comparisons, swaps = self.algo.get_counts()
        text = f"So sánh: {comparisons} | Hoán đổi: {swaps}"
        if self.algo.is_done():
            text += " | Đã xong"
        self.counts_label.config(text=text)

        if not values:
            return
        # Lúc cửa sổ chưa hiện, winfo trả về 1: dùng kích thước mặc định
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            width, height = config.CANVAS_WIDTH, config.CANVAS_HEIGHT

        slot = width / len(values)
        top_margin = 20              # chừa chỗ cho số phía trên cộ
        max_value = max(values)
        for index, value in enumerate(values):
            x0 = index * slot + 2
            x1 = (index + 1) *slot - 2
            bar_height = (height - top_margin) * value / max_value # cao theo tỷ lệ
            y0 = height - bar_height
            self.canvas.create_rectangle(
                x0, y0, x1, height, fill=self._bar_color(index), outline=""
            )
            if slot >= 22:
                self.canvas.create_text((x0 + x1) / 2, y0 - 9, text=str(value))

    # ---------- chạy ----------
    def step_once(self):
        """Làm một bước và vẽ lại."""
        if self.algo.is_done():
            return
        self.highlight = self.algo.step() or ()
        if self.algo.is_done():
            self.highlight = ()
        self.draw()

    def _tick(self):
        self.step_once()
        if self.running and not self.algo.is_done():
            self.after_id = self.after(self.controls.get_delay(), self._tick)
        else:
            self.running = False
            self.after_id = None

    def start(self):
        if self.running or self.algo.is_done():
            return
        self.running = True
        self._tick()

    def pause(self):
        self.running = False
        if self.after_id is not None:
            self.after_cancel(self.after_id)    # huỷ lệnh đang chờ, tránh chạy chồng
            self.after_id = None

    def step_button(self):
        self.pause()
        self.step_once()

    def reset(self):
        self.pause()
        self.algo.reset()
        self.highlight = ()
        self.saved = False
        self.draw()

    # ---------- lưu phiên ----------
    def build_result(self):
        """Dict kết quả đúng mẫu đã thống nhất với Khoa."""
        copy = self.algorithms[self.combo.get()](self.base_values)
        start = time.perf_counter()
        copy.run_all()        # đo thuần thuật toán, không tính thời gian chờ hiệu ứng
        time_ms = (time.perf_counter() - start) * 1000
        comparisons, swaps = self.algo.get_counts()
        return {
            "algorithm": self.algo.get_name(),
            "values": list(self.base_values),  # dãy gốc, không phải dãy đã sắp xếp
            "comparisons": comparisons,
            "swaps": swaps,
            "time_ms": round(time_ms, 3),
        }

    def save_session(self):
        if not self.algo.is_done():
            messagebox.showwarning("Chưa xong", "Chạy xong rồi mới lưu được.")
            return
        if self.saved:
            messagebox.showinfo("Đã lưu", "Phiên này đã được lưu rồi.")
            return
        if self.on_finish is None:
            messagebox.showinfo("Chưa kết nối", "Chưa có nơi nhận kết quả (on_finish).")
            return
        self.saved = True
        self.on_finish(self.build_result())
        messagebox.showinfo("Đã lưu", "Đã lưu phiên.")

    def destroy(self):
        self.pause()               # huỷ .after() trước khi đóng cửa sổ
        super().destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("SortPanel - chạy thử")
    panel = SortPanel(root, on_finish=print)
    panel.pack(fill="both", expand=True)
    root.mainloop()