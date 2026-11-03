"""Cửa sổ chính: ghép CanvasView + ControlPanel + SortRunner, điều khiển vòng lặp hoạt hình."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from algorithms import algorithm_names, create
from algorithms.base import Step, StepType
from core import data_manager as dm
from core.runner import RunState, SortRunner, speed_to_timing
from ui.benchmark_window import BenchmarkWindow
from ui.canvas_view import CanvasView, ColorLegend
from ui.control_panel import ControlPanel

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

FILE_TYPES = [("Dữ liệu JSON/CSV", "*.json *.csv"), ("JSON", "*.json"), ("CSV", "*.csv")]


def describe_step(step: Optional[Step], data: List[int]) -> str:
    """Câu mô tả bước vừa thực hiện, hiển thị dưới Canvas."""
    if step is None:
        return ""
    t, idx = step.type, step.indices
    if t is StepType.COMPARE:
        i, j = idx
        return f"So sánh a[{i}] = {data[i]} với a[{j}] = {data[j]}"
    if t is StepType.SWAP:
        i, j = idx
        return f"Hoán đổi a[{i}] và a[{j}] → {data[i]} ⇄ {data[j]}"
    if t is StepType.OVERWRITE:
        return f"Ghi đè a[{idx[0]}] = {data[idx[0]]}"
    if t is StepType.PIVOT:
        return f"Chọn phần tử chốt a[{idx[0]}] = {data[idx[0]]}"
    if t is StepType.DONE:
        return "Dãy đã được sắp xếp xong ✔"
    return ""


class SortingApp:
    """Lớp ứng dụng: nhận callback từ ControlPanel và cập nhật CanvasView."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Hệ thống trực quan hóa thuật toán sắp xếp")
        height = min(760, max(480, root.winfo_screenheight() - 90))   # không vượt quá màn hình
        root.geometry(f"1200x{height}")
        root.minsize(940, 480)
        try:
            ttk.Style(root).theme_use("clam")
        except tk.TclError:
            pass

        self.runner = SortRunner()
        self.data: List[int] = dm.generate(30, "random", low=5, high=100)
        self.algorithm_name = algorithm_names()[0]
        self._after_id: Optional[str] = None
        self._bench_win: Optional[BenchmarkWindow] = None
        self._speed = 50

        callbacks = {
            "on_generate": self.on_generate,
            "on_apply_text": self.on_apply_text,
            "on_load_file": self.on_load_file,
            "on_save_array": self.on_save_array,
            "on_algorithm_change": self.on_algorithm_change,
            "on_start": self.on_start,
            "on_pause": self.on_pause,
            "on_resume": self.on_resume,
            "on_step": self.on_step,
            "on_reset": self.on_reset,
            "on_speed_change": self.on_speed_change,
            "on_benchmark": self.on_benchmark,
        }
        self.panel = ControlPanel(root, algorithm_names(), dm.SCENARIOS, callbacks)
        self.panel.pack(side="left", fill="y")

        right = ttk.Frame(root, padding=(0, 8, 8, 8))
        right.pack(side="left", fill="both", expand=True)
        self.title_var = tk.StringVar()
        ttk.Label(right, textvariable=self.title_var, font=("TkDefaultFont", 14, "bold")).pack(
            anchor="w")
        self.view = CanvasView(right)
        self.view.pack(fill="both", expand=True, pady=6)
        ColorLegend(right).pack(anchor="w")
        self.msg_var = tk.StringVar()
        ttk.Label(right, textvariable=self.msg_var, font=("TkDefaultFont", 11)).pack(
            anchor="w", pady=(4, 0))

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._reload()

    # ------------------------------------------------------------ nạp lại
    def _reload(self, message: str = "") -> None:
        """Tạo lại thuật toán từ self.data và đưa mọi thứ về trạng thái IDLE."""
        self._cancel_loop()
        algo = create(self.algorithm_name, self.data)
        self.runner.load(algo)
        self.view.set_data(self.data)
        self.panel.set_state(RunState.IDLE)
        self.panel.update_stats(0, 0, 0, 0)
        self.panel.set_algorithm_info(self._info_text(algo))
        self.title_var.set(f"{algo.name} — {len(self.data)} phần tử")
        self.msg_var.set(message or "Bấm 'Chạy' hoặc 'Từng bước' để bắt đầu.")

    @staticmethod
    def _info_text(algo) -> str:
        return (f"{algo.description}\n\nTốt nhất: {algo.time_best} · Trung bình: {algo.time_average}"
                f" · Xấu nhất: {algo.time_worst}\nBộ nhớ phụ: {algo.space} · "
                f"Ổn định: {'có' if algo.stable else 'không'}")

    # --------------------------------------------------------- dữ liệu
    def on_generate(self, size: int, scenario: str) -> None:
        if not 2 <= size <= dm.MAX_VISUAL_SIZE:
            messagebox.showerror("Kích thước không hợp lệ",
                                 f"Số phần tử phải từ 2 đến {dm.MAX_VISUAL_SIZE}.")
            return
        self.data = dm.generate(size, scenario, low=5, high=max(100, size * 2))
        self._reload(f"Đã sinh {size} số ({dm.SCENARIOS[scenario]}).")

    def on_apply_text(self, text: str) -> None:
        try:
            data = dm.parse_text(text)
            self._check_visual_size(data)
        except ValueError as e:
            messagebox.showerror("Dãy nhập không hợp lệ", str(e))
            return
        self.data = data
        self.panel.set_size(len(data))
        self._reload(f"Đã nhận {len(data)} số từ ô nhập.")

    def on_load_file(self) -> None:
        path = filedialog.askopenfilename(title="Nạp dãy số", initialdir=DATA_DIR,
                                          filetypes=FILE_TYPES)
        if not path:
            return
        try:
            data = dm.load_array(path)
            self._check_visual_size(data)
        except (ValueError, OSError) as e:
            messagebox.showerror("Không nạp được file", str(e))
            return
        self.data = data
        self.panel.set_size(len(data))
        self.panel.set_text("")
        self._reload(f"Đã nạp {len(data)} số từ {os.path.basename(path)}.")

    def on_save_array(self) -> None:
        path = filedialog.asksaveasfilename(title="Lưu dãy số", initialdir=DATA_DIR,
                                            defaultextension=".json",
                                            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")])
        if not path:
            return
        try:
            dm.save_array(path, self.data)   # lưu dãy GỐC (trước khi sắp xếp)
        except (ValueError, OSError) as e:
            messagebox.showerror("Không lưu được", str(e))
            return
        self.msg_var.set(f"Đã lưu dãy ban đầu vào {os.path.basename(path)}.")

    @staticmethod
    def _check_visual_size(data: List[int]) -> None:
        if len(data) < 2:
            raise ValueError("Cần ít nhất 2 phần tử để sắp xếp.")
        if len(data) > dm.MAX_VISUAL_SIZE:
            raise ValueError(f"Dãy có {len(data)} phần tử; hoạt hình chỉ hỗ trợ tối đa "
                             f"{dm.MAX_VISUAL_SIZE}. Hãy dùng 'So sánh hiệu năng' cho dãy lớn.")

    # ------------------------------------------------------- điều khiển
    def on_algorithm_change(self, name: str) -> None:
        self.algorithm_name = name
        self._reload(f"Đã chọn {name}.")

    def on_start(self) -> None:
        if self.runner.start():
            self.panel.set_state(RunState.RUNNING)
            self._schedule()

    def on_pause(self) -> None:
        if self.runner.pause():
            self._cancel_loop()
            self.panel.set_state(RunState.PAUSED)

    def on_resume(self) -> None:
        if self.runner.resume():
            self.panel.set_state(RunState.RUNNING)
            self._schedule()

    def on_step(self) -> None:
        step = self.runner.step_once()
        self._render(step)

    def on_reset(self) -> None:
        self._cancel_loop()
        self.runner.reset()
        self.view.set_data(self.data)
        self.panel.set_state(RunState.IDLE)
        self.panel.update_stats(0, 0, 0, 0)
        self.msg_var.set("Đã đặt lại. Bấm 'Chạy' để chạy lại từ đầu.")

    def on_speed_change(self, value: int) -> None:
        self._speed = value   # vòng lặp đọc giá trị này ở mỗi tick

    def on_benchmark(self) -> None:
        if self._bench_win is not None and self._bench_win.winfo_exists():
            self._bench_win.lift()
            self._bench_win.focus_force()
            return
        self._bench_win = BenchmarkWindow(self.root, algorithm_names(), RESULTS_DIR)

    # ------------------------------------------------- vòng lặp hoạt hình
    def _schedule(self) -> None:
        self._cancel_loop()
        delay, _ = speed_to_timing(self._speed)
        self._after_id = self.root.after(delay, self._tick)

    def _cancel_loop(self) -> None:
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self) -> None:
        self._after_id = None
        if not self.runner.is_running:
            return
        _, per_tick = speed_to_timing(self._speed)
        step = self.runner.tick(per_tick)
        self._render(step)
        if self.runner.is_running:
            self._schedule()

    def _render(self, step: Optional[Step]) -> None:
        algo = self.runner.algorithm
        self.view.render(algo.data, step)
        self.panel.update_stats(algo.comparisons, algo.swaps, algo.overwrites, algo.steps_count)
        self.panel.set_state(self.runner.state)
        if step is not None:
            self.msg_var.set(describe_step(step, algo.data))

    def _on_close(self) -> None:
        self._cancel_loop()
        if self._bench_win is not None and self._bench_win.winfo_exists():
            self._bench_win.destroy()
        self.root.destroy()


def run() -> None:
    root = tk.Tk()
    SortingApp(root)
    root.mainloop()
