"""ControlPanel: bảng điều khiển tự xây dựng (kế thừa ttk.Frame).

Panel KHÔNG chứa logic nghiệp vụ. Mọi hành động của người dùng được chuyển ra ngoài
qua các callback do lớp ứng dụng truyền vào, nhờ đó panel độc lập, dễ thay thế/tái sử dụng.

Các khoá callback được hỗ trợ
-----------------------------
on_generate(size:int, scenario_key:str)   on_apply_text(text:str)
on_load_file()                            on_save_array()
on_algorithm_change(name:str)
on_start()  on_pause()  on_resume()  on_step()  on_reset()
on_speed_change(value:int)
on_benchmark()
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Sequence

from core.data_manager import MAX_VISUAL_SIZE
from core.runner import RunState

STATE_TEXT = {
    RunState.IDLE: "Sẵn sàng",
    RunState.RUNNING: "Đang chạy…",
    RunState.PAUSED: "Tạm dừng",
    RunState.FINISHED: "Hoàn thành ✔",
}


class ControlPanel(ttk.Frame):
    def __init__(self, master, algorithm_names: Sequence[str],
                 scenarios: Dict[str, str], callbacks: Dict[str, Callable], **kwargs):
        super().__init__(master, **kwargs)
        self._build_scroll_area()
        self._cb = dict(callbacks)
        self._scenario_labels = list(scenarios.values())
        self._label_to_key = {label: key for key, label in scenarios.items()}

        # biến Tk giữ giá trị của các ô nhập
        self.var_size = tk.IntVar(value=30)
        self.var_scenario = tk.StringVar(value=self._scenario_labels[0])
        self.var_text = tk.StringVar(value="")
        self.var_algorithm = tk.StringVar(value=algorithm_names[0])
        self.var_speed = tk.DoubleVar(value=50)
        self.var_speed_text = tk.StringVar(value="50")
        self.var_state = tk.StringVar(value=STATE_TEXT[RunState.IDLE])
        self.var_cmp = tk.StringVar(value="0")
        self.var_swap = tk.StringVar(value="0")
        self.var_write = tk.StringVar(value="0")
        self.var_steps = tk.StringVar(value="0")
        self.var_info = tk.StringVar(value="")

        self._build_data_section()
        self._build_algorithm_section(algorithm_names)
        self._build_run_section()
        self._build_speed_section()
        self._build_stats_section()
        ttk.Button(self._body, text="📊  So sánh hiệu năng…",
                   command=lambda: self._call("on_benchmark")).pack(fill="x", pady=(8, 0))
        self.set_state(RunState.IDLE)

    # ------------------------------------------------- vùng cuộn (scroll)
    def _build_scroll_area(self) -> None:
        """Tạo Canvas + Scrollbar bao quanh một khung chứa (self._body).

        Nhờ vậy bảng điều khiển vẫn dùng được khi cửa sổ thấp hơn nội dung:
        kéo thanh cuộn bên phải hoặc lăn chuột khi con trỏ nằm trên bảng.
        """
        try:
            bg = ttk.Style(self).lookup("TFrame", "background") or None
        except tk.TclError:
            bg = None
        canvas_kw = dict(highlightthickness=0, borderwidth=0)
        if bg:
            canvas_kw["bg"] = bg
        self._canvas = tk.Canvas(self, **canvas_kw)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._body = ttk.Frame(self._canvas, padding=8)
        self._body_window = self._canvas.create_window((0, 0), window=self._body, anchor="nw")
        self._body.bind("<Configure>", self._on_body_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # lăn chuột: chỉ bắt sự kiện khi con trỏ đang ở trên bảng điều khiển
        self.bind("<Enter>", self._bind_wheel)
        self.bind("<Leave>", self._unbind_wheel)

    def _on_body_configure(self, _event=None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        # độ rộng canvas vừa khít nội dung (không phải kéo ngang)
        self._canvas.configure(width=self._body.winfo_reqwidth())

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfigure(self._body_window, width=event.width)

    def _bind_wheel(self, _event=None) -> None:
        self.bind_all("<MouseWheel>", self._on_wheel)       # Windows / macOS
        self.bind_all("<Button-4>", self._on_wheel)         # Linux: cuộn lên
        self.bind_all("<Button-5>", self._on_wheel)         # Linux: cuộn xuống

    def _unbind_wheel(self, _event=None) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_wheel(self, event) -> None:
        first, last = self._canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return                                          # nội dung vừa khít, không cần cuộn
        num = getattr(event, "num", 0)
        if num == 4:
            direction = -1
        elif num == 5:
            direction = 1
        else:
            direction = -1 if event.delta > 0 else 1
        self._canvas.yview_scroll(direction, "units")

    # ------------------------------------------------------------------ UI
    def _section(self, title: str) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self._body, text=title, padding=6)
        frame.pack(fill="x", pady=(0, 6))
        return frame

    def _build_data_section(self) -> None:
        box = self._section("1. Dữ liệu")
        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Label(row, text="Số phần tử:").pack(side="left")
        ttk.Spinbox(row, from_=2, to=MAX_VISUAL_SIZE, width=6,
                    textvariable=self.var_size).pack(side="left", padx=4)
        ttk.Combobox(box, textvariable=self.var_scenario, values=self._scenario_labels,
                     state="readonly").pack(fill="x", pady=4)
        ttk.Button(box, text="🎲  Sinh dãy số",
                   command=self._on_generate).pack(fill="x")

        ttk.Label(box, text="Hoặc nhập tay (cách nhau bởi dấu , hoặc khoảng trắng):").pack(
            anchor="w", pady=(8, 2))
        ttk.Entry(box, textvariable=self.var_text).pack(fill="x")
        ttk.Button(box, text="Áp dụng dãy nhập",
                   command=lambda: self._call("on_apply_text", self.var_text.get())).pack(
            fill="x", pady=(4, 0))

        row2 = ttk.Frame(box)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Button(row2, text="📂 Nạp file…",
                   command=lambda: self._call("on_load_file")).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(row2, text="💾 Lưu dãy…",
                   command=lambda: self._call("on_save_array")).pack(
            side="left", expand=True, fill="x", padx=(2, 0))

    def _build_algorithm_section(self, names: Sequence[str]) -> None:
        box = self._section("2. Thuật toán")
        combo = ttk.Combobox(box, textvariable=self.var_algorithm, values=list(names),
                             state="readonly")
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>",
                   lambda _e: self._call("on_algorithm_change", self.var_algorithm.get()))
        ttk.Label(box, textvariable=self.var_info, wraplength=250, justify="left").pack(
            fill="x", pady=(6, 0))

    def _build_run_section(self) -> None:
        box = self._section("3. Điều khiển")
        grid = ttk.Frame(box)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        self.btn_start = ttk.Button(grid, text="▶ Chạy", command=lambda: self._call("on_start"))
        self.btn_pause = ttk.Button(grid, text="⏸ Tạm dừng", command=lambda: self._call("on_pause"))
        self.btn_resume = ttk.Button(grid, text="⏯ Tiếp tục", command=lambda: self._call("on_resume"))
        self.btn_step = ttk.Button(grid, text="⏭ Từng bước", command=lambda: self._call("on_step"))
        self.btn_reset = ttk.Button(grid, text="↺ Đặt lại", command=lambda: self._call("on_reset"))
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=2)
        self.btn_pause.grid(row=0, column=1, sticky="ew", padx=(2, 0), pady=2)
        self.btn_resume.grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=2)
        self.btn_step.grid(row=1, column=1, sticky="ew", padx=(2, 0), pady=2)
        self.btn_reset.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)

    def _build_speed_section(self) -> None:
        box = self._section("4. Tốc độ")
        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Label(row, text="Chậm").pack(side="left")
        ttk.Scale(row, from_=1, to=100, orient="horizontal", variable=self.var_speed,
                  command=self._on_speed).pack(side="left", expand=True, fill="x", padx=6)
        ttk.Label(row, text="Nhanh").pack(side="left")
        ttk.Label(box, textvariable=self.var_speed_text).pack()

    def _build_stats_section(self) -> None:
        box = self._section("5. Thống kê")
        rows = [("Trạng thái:", self.var_state), ("Số lần so sánh:", self.var_cmp),
                ("Số lần hoán đổi:", self.var_swap), ("Số lần ghi đè:", self.var_write),
                ("Tổng số bước:", self.var_steps)]
        for r, (label, var) in enumerate(rows):
            ttk.Label(box, text=label).grid(row=r, column=0, sticky="w")
            ttk.Label(box, textvariable=var, font=("TkDefaultFont", 10, "bold")).grid(
                row=r, column=1, sticky="e", padx=(12, 0))
        box.columnconfigure(1, weight=1)

    # ------------------------------------------------------------ sự kiện
    def _call(self, name: str, *args) -> None:
        fn = self._cb.get(name)
        if fn is not None:
            fn(*args)

    def _on_generate(self) -> None:
        try:
            size = int(self.var_size.get())
        except (tk.TclError, ValueError):
            size = -1  # để lớp ứng dụng báo lỗi thống nhất
        key = self._label_to_key.get(self.var_scenario.get(), "random")
        self._call("on_generate", size, key)

    def _on_speed(self, value) -> None:
        speed = max(1, min(100, int(float(value))))
        self.var_speed_text.set(str(speed))
        self._call("on_speed_change", speed)

    # ----------------------------------------------------- API cho App gọi
    def set_state(self, state: RunState) -> None:
        """Bật/tắt các nút điều khiển theo trạng thái chạy."""
        enabled = {
            RunState.IDLE:     dict(start=1, pause=0, resume=0, step=1, reset=1),
            RunState.RUNNING:  dict(start=0, pause=1, resume=0, step=0, reset=1),
            RunState.PAUSED:   dict(start=0, pause=0, resume=1, step=1, reset=1),
            RunState.FINISHED: dict(start=0, pause=0, resume=0, step=0, reset=1),
        }[state]
        buttons = dict(start=self.btn_start, pause=self.btn_pause, resume=self.btn_resume,
                       step=self.btn_step, reset=self.btn_reset)
        for key, btn in buttons.items():
            btn.state(["!disabled"] if enabled[key] else ["disabled"])
        self.var_state.set(STATE_TEXT[state])

    def update_stats(self, comparisons: int, swaps: int, overwrites: int, steps: int) -> None:
        self.var_cmp.set(f"{comparisons:,}")
        self.var_swap.set(f"{swaps:,}")
        self.var_write.set(f"{overwrites:,}")
        self.var_steps.set(f"{steps:,}")

    def set_algorithm_info(self, text: str) -> None:
        self.var_info.set(text)

    def get_speed(self) -> int:
        return max(1, min(100, int(float(self.var_speed.get()))))

    def set_text(self, text: str) -> None:
        self.var_text.set(text)

    def set_size(self, size: int) -> None:
        self.var_size.set(size)
