import os
import tempfile
import threading
import unittest

from algorithms import ALGORITHM_CLASSES, create
from algorithms.base import StepType
from core import data_manager as dm
from core.benchmark import BenchmarkConfig, format_table, run_benchmark
from core.runner import RunState, SortRunner, speed_to_timing


class TestSpeedMapping(unittest.TestCase):
    def test_bounds_and_monotonic(self):
        self.assertEqual(speed_to_timing(1), (1000, 1))
        self.assertEqual(speed_to_timing(100), (10, 10))
        self.assertEqual(speed_to_timing(-5), speed_to_timing(1))
        self.assertEqual(speed_to_timing(999), speed_to_timing(100))
        delays = [speed_to_timing(s)[0] for s in range(1, 101)]
        steps = [speed_to_timing(s)[1] for s in range(1, 101)]
        self.assertEqual(delays, sorted(delays, reverse=True))
        self.assertEqual(steps, sorted(steps))


class TestRunnerStateMachine(unittest.TestCase):
    def make(self, data=(4, 3, 2, 1)):
        r = SortRunner()
        r.load(create("bubble", data))
        return r

    def test_initial_state(self):
        r = self.make()
        self.assertIs(r.state, RunState.IDLE)
        self.assertIsNone(SortRunner().step_once())

    def test_valid_and_invalid_transitions(self):
        r = self.make()
        self.assertFalse(r.pause())
        self.assertFalse(r.resume())
        self.assertTrue(r.start())
        self.assertFalse(r.start())            # không chạy chồng
        self.assertTrue(r.pause())
        self.assertIs(r.state, RunState.PAUSED)
        self.assertTrue(r.resume())
        self.assertIs(r.state, RunState.RUNNING)

    def test_tick_only_when_running(self):
        r = self.make()
        self.assertIsNone(r.tick())
        r.start()
        self.assertIsNotNone(r.tick())
        r.pause()
        steps_before = r.algorithm.steps_count
        self.assertIsNone(r.tick(5))
        self.assertEqual(r.algorithm.steps_count, steps_before)

    def test_step_once_moves_to_paused(self):
        r = self.make()
        self.assertIsNotNone(r.step_once())
        self.assertIs(r.state, RunState.PAUSED)
        self.assertEqual(r.algorithm.steps_count, 1)
        r.resume()
        self.assertIsNone(r.step_once())       # đang RUNNING thì không bước tay

    def test_run_to_finish(self):
        r = self.make()
        r.start()
        guard = 0
        while r.is_running and guard < 10_000:
            r.tick(3)
            guard += 1
        self.assertIs(r.state, RunState.FINISHED)
        self.assertEqual(r.algorithm.data, [1, 2, 3, 4])
        self.assertFalse(r.start())
        self.assertIsNone(r.step_once())

    def test_manual_stepping_reaches_finished(self):
        r = self.make((2, 1))
        while r.state is not RunState.FINISHED:
            self.assertIsNotNone(r.step_once())
        self.assertEqual(r.last_step.type, StepType.DONE)

    def test_pause_resume_gives_same_result_as_uninterrupted(self):
        data = dm.generate(40, seed=2)
        r = self.make(data)
        r.start()
        while r.is_running:
            r.tick(7)
            if r.algorithm.steps_count % 2 == 0 and r.is_running:
                r.pause()
                r.step_once()
                r.resume()
        self.assertEqual(r.algorithm.data, sorted(data))

    def test_reset_returns_to_idle_and_restores_data(self):
        data = [5, 4, 3]
        r = self.make(data)
        r.start()
        r.tick(5)
        r.reset()
        self.assertIs(r.state, RunState.IDLE)
        self.assertEqual(r.algorithm.data, data)
        self.assertTrue(r.start())

    def test_trivial_arrays_finish_on_first_step(self):
        for data in ([], [1]):
            r = self.make(data)
            r.step_once()
            self.assertIs(r.state, RunState.FINISHED)


class TestBenchmark(unittest.TestCase):
    def test_rows_and_correctness(self):
        cfg = BenchmarkConfig(sizes=[20, 40], scenarios=["random", "sorted"], repeats=2)
        rows = run_benchmark(cfg)
        self.assertEqual(len(rows), len(ALGORITHM_CLASSES) * 2 * 2)
        for r in rows:
            self.assertTrue(r["correct"])
            self.assertEqual(r["repeats"], 2)
            self.assertGreaterEqual(r["time_ms"], 0)
        self.assertIn("Bubble Sort", format_table(rows))

    def test_deterministic_counters_with_seed(self):
        cfg = BenchmarkConfig(sizes=[30], repeats=2, seed=5)
        a, b = run_benchmark(cfg), run_benchmark(cfg)
        key = lambda rows: [(r["algorithm"], r["comparisons"], r["swaps"], r["overwrites"]) for r in rows]
        self.assertEqual(key(a), key(b))

    def test_expected_complexity_findings(self):
        cfg = BenchmarkConfig(sizes=[200], scenarios=["random", "sorted", "reversed"], repeats=1)
        rows = {(r["algorithm"], r["scenario"]): r for r in run_benchmark(cfg)}
        n = 200
        self.assertEqual(rows[("Bubble Sort", "sorted")]["comparisons"], n - 1)
        self.assertEqual(rows[("Insertion Sort", "sorted")]["comparisons"], n - 1)
        # dãy đảo ngược sinh từ số ngẫu nhiên có thể trùng giá trị -> số nghịch thế <= n(n-1)/2
        max_inv = n * (n - 1) / 2
        self.assertLessEqual(rows[("Bubble Sort", "reversed")]["swaps"], max_inv)
        self.assertGreater(rows[("Bubble Sort", "reversed")]["swaps"], 0.9 * max_inv)
        self.assertLess(rows[("Merge Sort", "random")]["comparisons"],
                        rows[("Bubble Sort", "random")]["comparisons"] / 5)
        self.assertGreater(rows[("Quick Sort", "sorted")]["comparisons"],
                           5 * rows[("Quick Sort", "random")]["comparisons"])   # trường hợp xấu

    def test_progress_row_callbacks_and_cancel(self):
        events, seen = [], []
        cfg = BenchmarkConfig(sizes=[10, 20], repeats=1)
        rows = run_benchmark(cfg, progress=lambda d, t, m: events.append((d, t)),
                             on_row=seen.append)
        self.assertEqual(len(rows), len(seen))
        self.assertEqual(events[-1], (len(rows), len(rows)))

        stop = threading.Event()
        stop.set()
        self.assertEqual(run_benchmark(cfg, cancel=stop), [])

    def test_invalid_config(self):
        for cfg in (BenchmarkConfig(repeats=0), BenchmarkConfig(algorithms=[]),
                    BenchmarkConfig(sizes=[]), BenchmarkConfig(scenarios=["xxx"])):
            with self.assertRaises(ValueError):
                run_benchmark(cfg)

    def test_save_results_file(self):
        with tempfile.TemporaryDirectory() as d:
            rows = run_benchmark(BenchmarkConfig(sizes=[10], repeats=1))
            path = dm.default_results_path(d)
            dm.save_results(path, rows)
            self.assertEqual(len(dm.load_results(path)), len(rows))


if __name__ == "__main__":
    unittest.main()
