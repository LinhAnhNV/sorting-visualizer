"""So sánh hiệu năng các thuật toán trên nhiều kích thước dãy (không cần UI)."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from algorithms import algorithm_names, get_class
from core.data_manager import SCENARIOS, generate

ProgressCb = Callable[[int, int, str], None]
RowCb = Callable[[dict], None]


@dataclass
class BenchmarkConfig:
    algorithms: List[str] = field(default_factory=algorithm_names)
    sizes: List[int] = field(default_factory=lambda: [50, 100, 200, 500, 1000])
    scenarios: List[str] = field(default_factory=lambda: ["random"])
    repeats: int = 3
    seed: Optional[int] = 42   # None = ngẫu nhiên mỗi lần chạy


def run_benchmark(config: BenchmarkConfig,
                  progress: Optional[ProgressCb] = None,
                  on_row: Optional[RowCb] = None,
                  cancel: Optional[threading.Event] = None) -> List[dict]:
    """Chạy benchmark và trả về danh sách dòng kết quả.

    Với mỗi (kịch bản, kích thước) các thuật toán đều sắp xếp *cùng* các bộ dữ liệu
    để so sánh công bằng. Số liệu là trung bình của ``repeats`` lần chạy.
    Thời gian đo bằng ``time.perf_counter`` quanh ``run_all()``; nó gồm cả chi phí
    sinh ``Step`` (như nhau cho mọi thuật toán) nên chỉ dùng để so sánh tương đối.
    """
    if config.repeats < 1:
        raise ValueError("Số lần lặp phải >= 1.")
    classes = [get_class(n) for n in config.algorithms]
    if not classes:
        raise ValueError("Chưa chọn thuật toán nào.")
    if not config.sizes:
        raise ValueError("Chưa chọn kích thước dãy nào.")
    for sc in config.scenarios:
        if sc not in SCENARIOS:
            raise ValueError(f"Kịch bản không hợp lệ: {sc!r}")

    total = len(config.scenarios) * len(config.sizes) * len(classes)
    done = 0
    results: List[dict] = []

    for scenario in config.scenarios:
        for size in config.sizes:
            datasets = []
            for rep in range(config.repeats):
                seed = None if config.seed is None else config.seed + 1000 * rep + size
                datasets.append(generate(size, scenario, high=max(100, size * 10), seed=seed))

            for cls in classes:
                if cancel is not None and cancel.is_set():
                    return results
                row = _measure(cls, datasets, scenario, size)
                results.append(row)
                done += 1
                if on_row:
                    on_row(row)
                if progress:
                    progress(done, total, f"{cls.name} · {SCENARIOS[scenario]} · n={size}")
    return results


def _measure(cls, datasets: List[List[int]], scenario: str, size: int) -> dict:
    totals: Dict[str, float] = {"comparisons": 0, "swaps": 0, "overwrites": 0,
                                "steps": 0, "time_ms": 0.0}
    correct = True
    for data in datasets:
        algo = cls(data)
        t0 = time.perf_counter()
        algo.run_all()
        elapsed = (time.perf_counter() - t0) * 1000.0
        correct = correct and algo.data == sorted(data)
        totals["comparisons"] += algo.comparisons
        totals["swaps"] += algo.swaps
        totals["overwrites"] += algo.overwrites
        totals["steps"] += algo.steps_count
        totals["time_ms"] += elapsed
    n = len(datasets)
    return {
        "algorithm": cls.name,
        "scenario": scenario,
        "size": size,
        "repeats": n,
        "comparisons": round(totals["comparisons"] / n, 1),
        "swaps": round(totals["swaps"] / n, 1),
        "overwrites": round(totals["overwrites"] / n, 1),
        "steps": round(totals["steps"] / n, 1),
        "time_ms": round(totals["time_ms"] / n, 3),
        "correct": correct,
    }


def format_table(rows: List[dict]) -> str:
    """Bảng chữ đẹp cho CLI."""
    header = f"{'Thuật toán':<15}{'Kịch bản':<22}{'n':>6}{'So sánh':>13}{'Hoán đổi':>12}{'Ghi đè':>11}{'ms':>10}  OK"
    lines = [header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r['algorithm']:<15}{SCENARIOS.get(r['scenario'], r['scenario']):<22}{r['size']:>6}"
            f"{r['comparisons']:>13,.0f}{r['swaps']:>12,.0f}{r['overwrites']:>11,.0f}"
            f"{r['time_ms']:>10.2f}  {'✔' if r['correct'] else '✘'}")
    return "\n".join(lines)
