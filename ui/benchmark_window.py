"""Cửa sổ so sánh hiệu năng: chạy benchmark ở thread nền, hiện bảng + biểu đồ."""
from __future__ import annotations

import math
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Sequence

from core.benchmark import BenchmarkConfig, run_benchmark
from core.data_manager import (SCENARIOS, default_results_path, parse_sizes,
                               save_results)

METRICS = {
    "Số lần so sánh": "comparisons",
    "Số lần hoán đổi": "swaps",
    "Số lần ghi đè": "overwrites",
    "Thời gian (ms)": "time_ms",
}
ALL_SCENARIOS = "Tất cả kịch bản"
PALETTE = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e84393"]
TABLE_COLUMNS = [("algorithm", "Thuật toán", 120), ("scenario", "Kịch bản", 130),
                 ("size", "n", 60), ("comparisons", "So sánh", 90), ("swaps", "Hoán đổi", 90),
                 ("overwrites", "Ghi đè", 90), ("steps", "Số bước", 90),
                 ("time_ms", "Thời gian (ms)", 100), ("correct", "Đúng", 50)]


def fmt_number(v: float) -> str:
    """Rút gọn số cho nhãn trục: 1.2K, 3.4M ..."""
    a = abs(v)
    if a >= 1e9:
        return f"{v / 1e9:.3g}G"
    if a >= 1e6:
        return f"{v / 1e6:.3g}M"
    if a >= 1e3:
        return f"{v / 1e3:.3g}K"
    if a >= 10 or float(v).is_integer():
        return f"{v:.0f}"
    return f"{v:.2g}"


class BenchmarkWindow(tk.Toplevel):
    def __init__(self, master, algorithm_names: Sequence[str], results_dir: str):
        super().__init__(master)
        self.title("So sánh hiệu năng các thuật toán")
        self.geometry("1020x680")
        self.minsize(820, 560)
        self._names = list(algorithm_names)
        self._results_dir = results_dir
        self._queue: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._cancel = threading.Event()
        self._results: List[dict] = []
        self._closed = False
        self._label_to_key = {v: k for k, v in SCENARIOS.items()}

        self.var_sizes = tk.StringVar(value="50, 100, 200, 500, 1000")
        self.var_scenario = tk.StringVar(value=SCENARIOS["random"])
        self.var_repeats = tk.IntVar(value=3)
        self.var_algos: Dict[str, tk.BooleanVar] = {n: tk.BooleanVar(value=True) for n in self._names}
        self.var_status = tk.StringVar(value="Chọn cấu hình rồi bấm 'Chạy benchmark'.")
        self.var_metric = tk.StringVar(value=list(METRICS)[0])
        self.var_chart_scenario = tk.StringVar(value="")
        self.var_log = tk.BooleanVar(value=False)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        cfg = ttk.LabelFrame(self, text="Cấu hình", padding=8)
        cfg.pack(fill="x", padx=8, pady=(8, 4))

        r1 = ttk.Frame(cfg)
        r1.pack(fill="x")
        ttk.Label(r1, text="Kích thước dãy:").pack(side="left")
        ttk.Entry(r1, textvariable=self.var_sizes, width=28).pack(side="left", padx=(4, 12))
        ttk.Label(r1, text="Kịch bản:").pack(side="left")
        ttk.Combobox(r1, textvariable=self.var_scenario, state="readonly", width=22,
                     values=[ALL_SCENARIOS] + list(SCENARIOS.values())).pack(side="left", padx=(4, 12))
        ttk.Label(r1, text="Số lần lặp:").pack(side="left")
        ttk.Spinbox(r1, from_=1, to=10, width=4, textvariable=self.var_repeats).pack(
            side="left", padx=4)

        r2 = ttk.Frame(cfg)
        r2.pack(fill="x", pady=(6, 0))
        ttk.Label(r2, text="Thuật toán:").pack(side="left")
        for n in self._names:
            ttk.Checkbutton(r2, text=n, variable=self.var_algos[n]).pack(side="left", padx=6)

        r3 = ttk.Frame(cfg)
        r3.pack(fill="x", pady=(8, 0))
        self.btn_run = ttk.Button(r3, text="▶ Chạy benchmark", command=self._start)
        self.btn_run.pack(side="left")
        self.btn_stop = ttk.Button(r3, text="■ Dừng", command=self._stop)
        self.btn_stop.pack(side="left", padx=6)
        self.btn_stop.state(["disabled"])
        self.btn_export = ttk.Button(r3, text="💾 Xuất kết quả…", command=self._export)
        self.btn_export.pack(side="left")
        self.progress = ttk.Progressbar(r3, maximum=100, length=220)
        self.progress.pack(side="right")

        ttk.Label(self, textvariable=self.var_status, wraplength=980).pack(
            fill="x", padx=10, pady=2)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self._build_table_tab(nb)
        self._build_chart_tab(nb)

    def _build_table_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="Bảng kết quả")
        cols = [c[0] for c in TABLE_COLUMNS]
        self.tree = ttk.Treeview(tab, columns=cols, show="headings")
        for key, title, width in TABLE_COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center" if key != "algorithm" else "w")
        sb = ttk.Scrollbar(tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_chart_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="Biểu đồ")
        bar = ttk.Frame(tab, padding=4)
        bar.pack(fill="x")
        ttk.Label(bar, text="Đại lượng:").pack(side="left")
        cb1 = ttk.Combobox(bar, textvariable=self.var_metric, values=list(METRICS),
                           state="readonly", width=18)
        cb1.pack(side="left", padx=(4, 12))
        ttk.Label(bar, text="Kịch bản:").pack(side="left")
        self.cb_chart_scenario = ttk.Combobox(bar, textvariable=self.var_chart_scenario,
                                              state="readonly", width=22)
        self.cb_chart_scenario.pack(side="left", padx=(4, 12))
        ttk.Checkbutton(bar, text="Thang log", variable=self.var_log,
                        command=self._draw_chart).pack(side="left")
        cb1.bind("<<ComboboxSelected>>", lambda _e: self._draw_chart())
        self.cb_chart_scenario.bind("<<ComboboxSelected>>", lambda _e: self._draw_chart())

        self.chart = tk.Canvas(tab, bg="#ffffff", highlightthickness=0)
        self.chart.pack(fill="both", expand=True)
        self.chart.bind("<Configure>", lambda _e: self._draw_chart())

    # ---------------------------------------------------------- điều khiển
    def _start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        try:
            sizes = parse_sizes(self.var_sizes.get())
            repeats = int(self.var_repeats.get())
            if not 1 <= repeats <= 10:
                raise ValueError("Số lần lặp phải từ 1 đến 10.")
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("Cấu hình không hợp lệ", str(e), parent=self)
            return
        algos = [n for n in self._names if self.var_algos[n].get()]
        if not algos:
            messagebox.showerror("Cấu hình không hợp lệ", "Hãy chọn ít nhất một thuật toán.",
                                 parent=self)
            return
        label = self.var_scenario.get()
        scenarios = list(SCENARIOS) if label == ALL_SCENARIOS else [self._label_to_key[label]]

        config = BenchmarkConfig(algorithms=algos, sizes=sizes, scenarios=scenarios,
                                 repeats=repeats, seed=42)
        self._results = []
        self.tree.delete(*self.tree.get_children())
        self.progress["value"] = 0
        self._cancel.clear()
        self.btn_run.state(["disabled"])
        self.btn_stop.state(["!disabled"])
        self.var_status.set("Đang chạy benchmark…")

        self._thread = threading.Thread(target=self._worker, args=(config,), daemon=True)
        self._thread.start()
        self.after(100, self._poll)

    def _stop(self) -> None:
        self._cancel.set()
        self.var_status.set("Đang dừng…")

    def _worker(self, config: BenchmarkConfig) -> None:
        """Chạy ở thread nền; chỉ giao tiếp với UI qua hàng đợi (không đụng widget)."""
        try:
            rows = run_benchmark(
                config,
                progress=lambda d, t, m: self._queue.put(("progress", d, t, m)),
                on_row=lambda r: self._queue.put(("row", r)),
                cancel=self._cancel)
            self._queue.put(("finished", rows, self._cancel.is_set()))
        except Exception as exc:  # noqa: BLE001 - báo mọi lỗi về UI
            self._queue.put(("error", str(exc)))

    def _poll(self) -> None:
        if self._closed or not self.winfo_exists():
            return
        finished = False
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, done, total, text = msg
                    self.progress["value"] = 100.0 * done / max(total, 1)
                    self.var_status.set(f"Đang chạy ({done}/{total}): {text}")
                elif kind == "row":
                    self._add_row(msg[1])
                elif kind == "finished":
                    self._on_finished(msg[1], cancelled=msg[2])
                    finished = True
                elif kind == "error":
                    self._on_error(msg[1])
                    finished = True
        except queue.Empty:
            pass
        if not finished:
            self.after(100, self._poll)

    def _add_row(self, row: dict) -> None:
        self._results.append(row)
        values = []
        for key, _title, _w in TABLE_COLUMNS:
            v = row[key]
            if key == "scenario":
                v = SCENARIOS.get(v, v)
            elif key == "correct":
                v = "✔" if v else "✘"
            elif key in ("comparisons", "swaps", "overwrites", "steps"):
                v = f"{v:,.0f}"
            elif key == "time_ms":
                v = f"{v:,.2f}"
            values.append(v)
        self.tree.insert("", "end", values=values)

    def _on_finished(self, rows: List[dict], cancelled: bool) -> None:
        self.btn_run.state(["!disabled"])
        self.btn_stop.state(["disabled"])
        self._results = list(rows)
        scen_labels = [SCENARIOS[s] for s in dict.fromkeys(r["scenario"] for r in rows)]
        self.cb_chart_scenario.configure(values=scen_labels)
        if scen_labels:
            self.var_chart_scenario.set(scen_labels[0])
        self._draw_chart()
        if cancelled:
            self.var_status.set(f"Đã dừng. Có {len(rows)} dòng kết quả (chưa tự động lưu).")
            return
        self.progress["value"] = 100
        try:
            path = default_results_path(self._results_dir)
            save_results(path, rows)
            self.var_status.set(f"Hoàn thành {len(rows)} phép đo. Đã lưu kết quả: {path}")
        except OSError as e:
            self.var_status.set(f"Hoàn thành nhưng không lưu được file: {e}")

    def _on_error(self, text: str) -> None:
        self.btn_run.state(["!disabled"])
        self.btn_stop.state(["disabled"])
        self.var_status.set(f"Lỗi: {text}")
        messagebox.showerror("Lỗi benchmark", text, parent=self)

    def _export(self) -> None:
        if not self._results:
            messagebox.showinfo("Chưa có dữ liệu", "Hãy chạy benchmark trước.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".json", initialdir=self._results_dir,
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")], title="Xuất kết quả")
        if not path:
            return
        try:
            save_results(path, self._results)
            self.var_status.set(f"Đã xuất: {path}")
        except (OSError, ValueError) as e:
            messagebox.showerror("Không lưu được", str(e), parent=self)

    def _on_close(self) -> None:
        self.destroy()

    def destroy(self) -> None:
        """Dù đóng bằng nút X hay do cửa sổ chính huỷ, đều dừng thread và vòng poll."""
        self._closed = True
        self._cancel.set()
        super().destroy()

    # ------------------------------------------------------------ biểu đồ
    def _draw_chart(self) -> None:
        c = self.chart
        c.delete("all")
        w, h = max(c.winfo_width(), 300), max(c.winfo_height(), 200)
        scen_label = self.var_chart_scenario.get()
        scen_key = self._label_to_key.get(scen_label)
        rows = [r for r in self._results if r["scenario"] == scen_key]
        if not rows:
            c.create_text(w / 2, h / 2, text="Chưa có dữ liệu – hãy chạy benchmark.",
                          fill="#888888")
            return

        metric = METRICS[self.var_metric.get()]
        use_log = self.var_log.get()
        sizes = sorted({r["size"] for r in rows})
        algos = [n for n in self._names if any(r["algorithm"] == n for r in rows)]

        def tf(v: float) -> float:
            return math.log10(max(v, 1e-3)) if use_log else v

        values = [tf(r[metric]) for r in rows]
        if use_log:
            ymin, ymax = math.floor(min(values)), math.ceil(max(values))
            if ymax <= ymin:
                ymax = ymin + 1
        else:
            ymin, ymax = 0.0, (max(values) or 1.0)

        left, right, top, bottom = 70, 150, 20, 45
        pw, ph = w - left - right, h - top - bottom

        def px(size: int) -> float:
            if len(sizes) == 1:
                return left + pw / 2
            return left + (size - sizes[0]) / (sizes[-1] - sizes[0]) * pw

        def py(v: float) -> float:
            return top + ph - (tf(v) - ymin) / (ymax - ymin) * ph

        # lưới + nhãn trục Y
        ticks = 5
        for i in range(ticks + 1):
            yv = ymin + (ymax - ymin) * i / ticks
            y = top + ph - ph * i / ticks
            c.create_line(left, y, left + pw, y, fill="#e5e5e5")
            label = fmt_number(10 ** yv) if use_log else fmt_number(yv)
            c.create_text(left - 6, y, text=label, anchor="e", fill="#444444")
        c.create_line(left, top, left, top + ph, fill="#444444")
        c.create_line(left, top + ph, left + pw, top + ph, fill="#444444")
        for s in sizes:
            c.create_line(px(s), top + ph, px(s), top + ph + 4, fill="#444444")
            c.create_text(px(s), top + ph + 16, text=str(s), fill="#444444")
        c.create_text(left + pw / 2, h - 8, text="Kích thước dãy n", fill="#444444")

        # đường của từng thuật toán + chú giải
        for idx, name in enumerate(algos):
            color = PALETTE[idx % len(PALETTE)]
            pts = sorted(((r["size"], r[metric]) for r in rows if r["algorithm"] == name))
            coords = []
            for s, v in pts:
                coords += [px(s), py(v)]
            if len(coords) >= 4:
                c.create_line(*coords, fill=color, width=2)
            for s, v in pts:
                c.create_oval(px(s) - 3, py(v) - 3, px(s) + 3, py(v) + 3, fill=color, outline=color)
            ly = top + 10 + idx * 22
            c.create_line(left + pw + 16, ly, left + pw + 40, ly, fill=color, width=3)
            c.create_text(left + pw + 46, ly, text=name, anchor="w", fill="#222222")
