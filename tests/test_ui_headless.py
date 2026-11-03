"""Kiểm thử logic giao diện bằng tkinter giả (xem fake_tk.py) - chạy được trên máy không có màn hình."""
import os
import tempfile
import unittest

from tests import fake_tk

_fake = None
_restore = None
app_mod = canvas_mod = bench_mod = None


def setUpModule():
    global _fake, _restore, app_mod, canvas_mod, bench_mod
    _fake, _restore = fake_tk.install()
    import ui.app as a
    import ui.benchmark_window as b
    import ui.canvas_view as c
    app_mod, bench_mod, canvas_mod = a, b, c


def tearDownModule():
    _restore()


from algorithms import algorithm_names   # noqa: E402
from algorithms.base import Step, StepType  # noqa: E402
from core import data_manager as dm      # noqa: E402
from core.runner import RunState         # noqa: E402


class AppTestCase(unittest.TestCase):
    def setUp(self):
        fake_tk.SCHEDULE.clear()
        _fake["tkinter.messagebox"].calls.clear()
        self.root = _fake["tkinter"].Tk()
        self.app = app_mod.SortingApp(self.root)
        self.panel = self.app.panel
        self.view = self.app.view

    def bar_fills(self):
        rects = [it for it in self.view.items.values() if it["kind"] == "rect"]
        return [r["fill"] for r in rects]

    def errors(self):
        return _fake["tkinter.messagebox"].calls


class TestInitialState(AppTestCase):
    def test_initial_layout(self):
        self.assertIs(self.app.runner.state, RunState.IDLE)
        self.assertEqual(len(self.bar_fills()), 30)
        self.assertTrue(all(c == canvas_mod.BASE_COLOR for c in self.bar_fills()))
        self.assertFalse(self.panel.btn_start._disabled)
        self.assertTrue(self.panel.btn_pause._disabled)
        self.assertTrue(self.panel.btn_resume._disabled)
        self.assertFalse(self.panel.btn_step._disabled)
        self.assertEqual(self.panel.var_state.get(), "Sẵn sàng")
        self.assertIn("Bubble Sort", self.app.title_var.get())

    def test_labels_shown_for_few_bars_only(self):
        texts = [i for i in self.view.items.values() if i["kind"] == "text"]
        self.assertEqual(len(texts), 30)
        self.app.on_generate(120, "random")
        texts = [i for i in self.view.items.values() if i["kind"] == "text"]
        self.assertEqual(len(texts), 0)


class TestRunFlow(AppTestCase):
    def test_full_run_every_algorithm(self):
        for name in algorithm_names():
            with self.subTest(algorithm=name):
                self.app.on_algorithm_change(name)
                self.panel.btn_start.invoke()
                self.assertIs(self.app.runner.state, RunState.RUNNING)
                self.assertEqual(len(fake_tk.SCHEDULE), 1)      # đúng một vòng lặp after
                fake_tk.run_pending()
                algo = self.app.runner.algorithm
                self.assertIs(self.app.runner.state, RunState.FINISHED)
                self.assertEqual(algo.data, sorted(self.app.data))
                self.assertTrue(all(c == canvas_mod.COLORS[StepType.DONE] for c in self.bar_fills()))
                self.assertEqual(self.panel.var_state.get(), "Hoàn thành ✔")
                self.assertNotEqual(self.panel.var_steps.get(), "0")
                self.assertTrue(self.panel.btn_start._disabled)
                self.assertFalse(self.panel.btn_reset._disabled)
                self.assertEqual(fake_tk.SCHEDULE, [])

    def test_bars_follow_algorithm_data(self):
        self.panel.btn_start.invoke()
        fake_tk.run_n(5)
        rects = [it for it in self.view.items.values() if it["kind"] == "rect"]
        data = self.app.runner.algorithm.data
        heights = [r["coords"][3] - r["coords"][1] for r in rects]
        for i in range(len(data)):                       # cột cao hơn <=> giá trị lớn hơn
            for j in range(len(data)):
                if data[i] < data[j]:
                    self.assertLess(heights[i], heights[j])
        self.assertTrue(any(c != canvas_mod.BASE_COLOR for c in self.bar_fills()))

    def test_pause_resume_and_single_step(self):
        self.panel.btn_start.invoke()
        fake_tk.run_n(3)
        self.panel.btn_pause.invoke()
        self.assertIs(self.app.runner.state, RunState.PAUSED)
        self.assertEqual(fake_tk.SCHEDULE, [])                  # vòng lặp đã dừng
        self.assertFalse(self.panel.btn_resume._disabled)
        self.assertTrue(self.panel.btn_pause._disabled)

        before = self.app.runner.algorithm.steps_count
        self.panel.btn_step.invoke()
        self.assertEqual(self.app.runner.algorithm.steps_count, before + 1)
        self.assertIs(self.app.runner.state, RunState.PAUSED)
        self.assertNotEqual(self.app.msg_var.get(), "")

        self.panel.btn_resume.invoke()
        self.assertIs(self.app.runner.state, RunState.RUNNING)
        self.assertEqual(len(fake_tk.SCHEDULE), 1)
        fake_tk.run_pending()
        self.assertIs(self.app.runner.state, RunState.FINISHED)
        self.assertEqual(self.app.runner.algorithm.data, sorted(self.app.data))

    def test_double_start_does_not_create_two_loops(self):
        self.panel.btn_start.invoke()
        self.app.on_start()
        self.assertEqual(len(fake_tk.SCHEDULE), 1)

    def test_step_only_until_finished(self):
        self.app.on_apply_text("3 1 2")
        guard = 0
        while self.app.runner.state is not RunState.FINISHED and guard < 100:
            self.panel.btn_step.invoke()
            guard += 1
        self.assertIs(self.app.runner.state, RunState.FINISHED)
        self.assertTrue(self.panel.btn_step._disabled)
        self.assertEqual(self.app.runner.algorithm.data, [1, 2, 3])

    def test_reset_while_running_cancels_loop(self):
        self.panel.btn_start.invoke()
        fake_tk.run_n(4)
        self.panel.btn_reset.invoke()
        self.assertEqual(fake_tk.SCHEDULE, [])
        self.assertIs(self.app.runner.state, RunState.IDLE)
        self.assertEqual(self.panel.var_cmp.get(), "0")
        self.assertTrue(all(c == canvas_mod.BASE_COLOR for c in self.bar_fills()))
        self.panel.btn_start.invoke()                       # chạy lại được từ đầu
        fake_tk.run_pending()
        self.assertIs(self.app.runner.state, RunState.FINISHED)

    def test_switching_algorithm_mid_run_stops_old_loop(self):
        self.panel.btn_start.invoke()
        fake_tk.run_n(3)
        self.app.on_algorithm_change("Quick Sort")
        self.assertEqual(fake_tk.SCHEDULE, [])
        self.assertIs(self.app.runner.state, RunState.IDLE)
        self.assertIn("Quick Sort", self.app.title_var.get())

    def test_speed_slider_changes_timing(self):
        self.panel._on_speed("100")
        self.assertEqual(self.app._speed, 100)
        self.assertEqual(self.panel.var_speed_text.get(), "100")
        self.panel.btn_start.invoke()
        steps_before = self.app.runner.algorithm.steps_count
        fake_tk.run_n(1)
        self.assertEqual(self.app.runner.algorithm.steps_count - steps_before, 10)   # 10 bước/tick

    def test_stats_update_during_run(self):
        self.panel.btn_start.invoke()
        fake_tk.run_n(10)
        algo = self.app.runner.algorithm
        self.assertEqual(self.panel.var_cmp.get(), f"{algo.comparisons:,}")
        self.assertEqual(self.panel.var_swap.get(), f"{algo.swaps:,}")


class TestDataInput(AppTestCase):
    def test_generate_valid_and_invalid(self):
        self.app.on_generate(50, "reversed")
        self.assertEqual(len(self.app.data), 50)
        self.assertEqual(self.app.data, sorted(self.app.data, reverse=True))
        for bad in (1, 0, -1, dm.MAX_VISUAL_SIZE + 1):
            self.app.on_generate(bad, "random")
        self.assertEqual(len(self.errors()), 4)
        self.assertEqual(len(self.app.data), 50)               # dữ liệu cũ giữ nguyên

    def test_generate_button_reads_widgets(self):
        self.panel.var_size.set(15)
        self.panel.var_scenario.set(dm.SCENARIOS["sorted"])
        self.panel._on_generate()
        self.assertEqual(len(self.app.data), 15)
        self.assertEqual(self.app.data, sorted(self.app.data))

    def test_apply_text(self):
        self.app.on_apply_text("9, 8 7;6")
        self.assertEqual(self.app.data, [9, 8, 7, 6])
        self.assertEqual(self.panel.var_size.get(), 4)
        for bad in ("", "a b", "5", " , "):
            self.app.on_apply_text(bad)
        self.assertEqual(len(self.errors()), 4)
        self.assertEqual(self.app.data, [9, 8, 7, 6])

    def test_load_and_save_file(self):
        with tempfile.TemporaryDirectory() as d:
            dlg = _fake["tkinter.filedialog"]
            dlg.open_result = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sample.json")
            self.app.on_load_file()
            self.assertEqual(len(self.app.data), 30)

            dlg.save_result = os.path.join(d, "out.csv")
            self.app.on_save_array()
            self.assertEqual(dm.load_array(dlg.save_result), self.app.data)

            bad = os.path.join(d, "bad.json")
            with open(bad, "w") as f:
                f.write("{oops")
            dlg.open_result = bad
            self.app.on_load_file()
            self.assertEqual(len(self.errors()), 1)

            dlg.open_result = ""                                # người dùng bấm Cancel
            self.app.on_load_file()
            self.assertEqual(len(self.errors()), 1)

    def test_save_saves_original_not_sorted(self):
        self.app.on_apply_text("3 2 1")
        self.panel.btn_start.invoke()
        fake_tk.run_pending()
        with tempfile.TemporaryDirectory() as d:
            _fake["tkinter.filedialog"].save_result = os.path.join(d, "o.json")
            self.app.on_save_array()
            self.assertEqual(dm.load_array(os.path.join(d, "o.json")), [3, 2, 1])

    def test_file_too_large_for_animation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "big.json")
            dm.save_array(p, list(range(dm.MAX_VISUAL_SIZE + 5)))
            _fake["tkinter.filedialog"].open_result = p
            self.app.on_load_file()
            self.assertEqual(len(self.errors()), 1)


class TestCanvasView(AppTestCase):
    def test_render_highlights(self):
        self.view.set_data([5, 3, 9, 1])
        self.view.render([5, 3, 9, 1], Step(StepType.COMPARE, (0, 1)))
        fills = self.bar_fills()
        self.assertEqual(fills[0], canvas_mod.COLORS[StepType.COMPARE])
        self.assertEqual(fills[1], canvas_mod.COLORS[StepType.COMPARE])
        self.assertEqual(fills[2], canvas_mod.BASE_COLOR)
        self.view.render([3, 5, 9, 1], Step(StepType.SWAP, (0, 1)))
        self.assertEqual(self.bar_fills()[0], canvas_mod.COLORS[StepType.SWAP])
        self.view.render([3, 5, 9, 1], Step(StepType.DONE, ()))
        self.assertTrue(all(c == canvas_mod.COLORS[StepType.DONE] for c in self.bar_fills()))

    def test_taller_value_gives_taller_bar(self):
        self.view.set_data([1, 5, 10])
        rects = [it for it in self.view.items.values() if it["kind"] == "rect"]
        heights = [r["coords"][3] - r["coords"][1] for r in rects]
        self.assertLess(heights[0], heights[1])
        self.assertLess(heights[1], heights[2])

    def test_equal_and_negative_values(self):
        self.view.set_data([4, 4, 4])
        self.view.set_data([-5, 0, 5])
        rects = [it for it in self.view.items.values() if it["kind"] == "rect"]
        self.assertTrue(all(r["coords"][3] > r["coords"][1] for r in rects))

    def test_resize_rebuilds_and_keeps_colors(self):
        self.view.set_data([2, 1])
        self.view.render([2, 1], Step(StepType.COMPARE, (0, 1)))
        self.view.event("<Configure>", types_event(1000, 600))
        self.assertEqual(len(self.bar_fills()), 2)
        self.assertEqual(self.bar_fills()[0], canvas_mod.COLORS[StepType.COMPARE])


def types_event(w, h):
    class E:
        width, height = w, h
    return E()


class TestDescribeStep(unittest.TestCase):
    def test_all_types_described(self):
        data = [5, 3, 9]
        for step in (Step(StepType.COMPARE, (0, 1)), Step(StepType.SWAP, (0, 1)),
                     Step(StepType.OVERWRITE, (2,)), Step(StepType.PIVOT, (2,)),
                     Step(StepType.DONE, ())):
            self.assertTrue(app_mod.describe_step(step, data))
        self.assertEqual(app_mod.describe_step(None, data), "")


class TestBenchmarkWindow(AppTestCase):
    def make_window(self, d):
        return bench_mod.BenchmarkWindow(self.root, algorithm_names(), d)

    def test_run_fills_table_and_saves_results(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.make_window(d)
            w.var_sizes.set("10, 30")
            w.var_repeats.set(1)
            w.var_scenario.set(dm.SCENARIOS["reversed"])
            w._start()
            self.assertTrue(w.btn_run._disabled)
            w._thread.join(timeout=30)
            fake_tk.run_pending()
            self.assertEqual(len(w.tree.rows), 5 * 2)
            self.assertFalse(w.btn_run._disabled)
            saved = [f for f in os.listdir(d) if f.endswith(".json")]
            self.assertEqual(len(saved), 1)
            self.assertEqual(len(dm.load_results(os.path.join(d, saved[0]))), 10)
            self.assertIn("Đã lưu", w.var_status.get())
            self.assertGreater(len([i for i in w.chart.items.values() if i["kind"] == "line"]), 5)

            for metric in bench_mod.METRICS:                    # thử mọi đại lượng + thang log
                for log in (False, True):
                    w.var_metric.set(metric)
                    w.var_log.set(log)
                    w._draw_chart()
                    self.assertGreater(len(w.chart.items), 10)

    def test_all_scenarios_option_and_algorithm_filter(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.make_window(d)
            w.var_sizes.set("10")
            w.var_repeats.set(1)
            w.var_scenario.set(bench_mod.ALL_SCENARIOS)
            for name in algorithm_names()[2:]:
                w.var_algos[name].set(False)
            w._start()
            w._thread.join(timeout=30)
            fake_tk.run_pending()
            self.assertEqual(len(w.tree.rows), 2 * len(dm.SCENARIOS))

    def test_invalid_config_shows_error_and_does_not_start(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.make_window(d)
            w.var_sizes.set("abc")
            w._start()
            self.assertIsNone(w._thread)
            w.var_sizes.set("100")
            w.var_repeats.set(0)
            w._start()
            w.var_repeats.set(1)
            for name in algorithm_names():
                w.var_algos[name].set(False)
            w._start()
            self.assertEqual(len(self.errors()), 3)

    def test_stop_returns_partial_results_without_autosave(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.make_window(d)
            w.var_sizes.set("10")
            w.var_repeats.set(1)
            w._cancel.set()
            w._queue.put(("finished", [], True))
            w._on_finished([], cancelled=True)
            self.assertEqual(os.listdir(d), [])
            self.assertIn("Đã dừng", w.var_status.get())

    def test_close_stops_polling_and_thread(self):
        with tempfile.TemporaryDirectory() as d:
            for how in ("button", "parent_destroy"):
                w = self.make_window(d)
                w.var_sizes.set("10")
                w.var_repeats.set(1)
                w._start()
                w._on_close() if how == "button" else w.destroy()
                self.assertTrue(w._cancel.is_set())
                w._thread.join(timeout=30)
                fake_tk.SCHEDULE.clear()
                w._poll()
                self.assertEqual(fake_tk.SCHEDULE, [])

    def test_app_opens_single_benchmark_window(self):
        self.app.on_benchmark()
        first = self.app._bench_win
        self.app.on_benchmark()
        self.assertIs(self.app._bench_win, first)
        first.destroy()
        self.app.on_benchmark()
        self.assertIsNot(self.app._bench_win, first)

    def test_fmt_number(self):
        f = bench_mod.fmt_number
        self.assertEqual(f(0), "0")
        self.assertEqual(f(950), "950")
        self.assertEqual(f(1500), "1.5K")
        self.assertEqual(f(2_500_000), "2.5M")
        self.assertEqual(f(0.25), "0.25")


class TestScrollablePanel(AppTestCase):
    """Bảng điều khiển phải cuộn được khi cửa sổ thấp hơn nội dung."""

    def test_all_widgets_live_inside_scrollable_body(self):
        panel = self.panel
        for btn in (panel.btn_start, panel.btn_pause, panel.btn_resume,
                    panel.btn_step, panel.btn_reset):
            node = btn
            while node is not None and node is not panel._body:
                node = node.master
            self.assertIs(node, panel._body)          # nút nằm trong khung cuộn
        windows = [i for i in panel._canvas.items.values() if i["kind"] == "window"]
        self.assertEqual(len(windows), 1)

    def test_scrollregion_and_width_follow_content(self):
        panel = self.panel
        panel._on_body_configure()
        self.assertEqual(panel._canvas.kw["scrollregion"], (0, 0, 300, 1000))
        self.assertEqual(panel._canvas.kw["width"], 300)

        class E:
            width = 320
        panel._on_canvas_configure(E())
        window = next(i for i in panel._canvas.items.values() if i["kind"] == "window")
        self.assertEqual(window["width"], 320)

    def test_mouse_wheel_scrolls_on_all_platforms(self):
        panel = self.panel

        class Ev:
            def __init__(self, delta=0, num=0):
                self.delta, self.num = delta, num

        panel._canvas.scrolled = []
        panel._on_wheel(Ev(delta=-120))      # Windows: lăn xuống
        panel._on_wheel(Ev(delta=120))       # Windows: lăn lên
        panel._on_wheel(Ev(delta=-1))        # macOS
        panel._on_wheel(Ev(num=4))           # Linux lên
        panel._on_wheel(Ev(num=5))           # Linux xuống
        dirs = [n for (_tag, n, _u) in panel._canvas.scrolled]
        self.assertEqual(dirs, [1, -1, 1, -1, 1])

    def test_no_scroll_when_content_fits(self):
        panel = self.panel
        panel._canvas._view = (0.0, 1.0)
        panel._canvas.scrolled = []

        class Ev:
            delta, num = -120, 0
        panel._on_wheel(Ev())
        self.assertEqual(panel._canvas.scrolled, [])

    def test_wheel_bound_only_while_mouse_over_panel(self):
        panel = self.panel
        calls = []
        panel.bind_all = lambda seq, fn: calls.append(("bind", seq))
        panel.unbind_all = lambda seq: calls.append(("unbind", seq))
        panel._bind_wheel()
        panel._unbind_wheel()
        self.assertEqual([c[0] for c in calls], ["bind"] * 3 + ["unbind"] * 3)
        self.assertIn(("bind", "<MouseWheel>"), calls)
        self.assertIn(("bind", "<Button-4>"), calls)

    def test_panel_still_works_after_refactor(self):
        self.panel.btn_start.invoke()
        fake_tk.run_pending()
        self.assertIs(self.app.runner.state, RunState.FINISHED)


class TestClose(AppTestCase):
    def test_close_cancels_loop(self):
        self.panel.btn_start.invoke()
        self.app._on_close()
        self.assertEqual(fake_tk.SCHEDULE, [])
        self.assertEqual(self.root._destroyed, True)


if __name__ == "__main__":
    unittest.main()
