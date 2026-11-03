"""Điểm vào của chương trình.

    python main.py                 # mở giao diện Tkinter
    python main.py --benchmark     # chạy benchmark bằng dòng lệnh, lưu kết quả JSON/CSV
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from algorithms import algorithm_names, get_class          # noqa: E402
from core.benchmark import BenchmarkConfig, format_table, run_benchmark  # noqa: E402
from core.data_manager import (SCENARIOS, default_results_path, parse_sizes,  # noqa: E402
                               save_results)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Hệ thống trực quan hóa thuật toán sắp xếp")
    p.add_argument("--benchmark", action="store_true",
                   help="chạy benchmark không giao diện rồi thoát")
    p.add_argument("--sizes", default="50,100,200,500,1000", help="các kích thước dãy, vd 100,500,1000")
    p.add_argument("--scenario", default="all", choices=["all", *SCENARIOS],
                   help="kịch bản dữ liệu (mặc định: all)")
    p.add_argument("--algorithms", default="all",
                   help="danh sách khoá thuật toán: bubble,selection,insertion,merge,quick")
    p.add_argument("--repeats", type=int, default=3, help="số lần lặp mỗi phép đo")
    p.add_argument("--out", help="file kết quả (.json hoặc .csv); mặc định data/results/benchmark_*.json")
    return p


def run_cli_benchmark(args) -> int:
    try:
        sizes = parse_sizes(args.sizes)
        names = (algorithm_names() if args.algorithms == "all"
                 else [get_class(t).name for t in args.algorithms.split(",") if t.strip()])
        scenarios = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
        config = BenchmarkConfig(algorithms=names, sizes=sizes, scenarios=scenarios,
                                 repeats=args.repeats)
        rows = run_benchmark(config, progress=lambda d, t, m: print(f"[{d}/{t}] {m}", file=sys.stderr))
    except (ValueError, KeyError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2
    print(format_table(rows))
    out = args.out or default_results_path(os.path.join(ROOT, "data", "results"))
    save_results(out, rows)
    print(f"\nĐã lưu kết quả: {out}")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.benchmark:
        return run_cli_benchmark(args)
    try:
        from ui.app import run
    except ImportError as e:
        print("Không khởi động được giao diện: thiếu tkinter "
              f"({e}).\nTrên Ubuntu/Debian: sudo apt install python3-tk", file=sys.stderr)
        return 1
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
