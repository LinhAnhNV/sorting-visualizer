"""Kiểm thử các thuật toán sắp xếp (không cần giao diện)."""
import random
import unittest

from algorithms import ALGORITHM_CLASSES, algorithm_names, create, get_class
from algorithms.base import SortingAlgorithm, Step, StepType


def sample_cases():
    rng = random.Random(1)
    return {
        "rỗng": [],
        "1 phần tử": [5],
        "2 phần tử đảo": [2, 1],
        "trùng lặp": [3, 1, 3, 1, 2, 2, 3],
        "toàn bằng nhau": [4] * 10,
        "đã sắp xếp": list(range(30)),
        "đảo ngược": list(range(30, 0, -1)),
        "có số âm": [5, -3, 0, -10, 8, -3],
        "ngẫu nhiên 100": [rng.randint(-50, 50) for _ in range(100)],
    }


class TestCorrectness(unittest.TestCase):
    def test_all_algorithms_match_sorted(self):
        for cls in ALGORITHM_CLASSES:
            for label, data in sample_cases().items():
                with self.subTest(algorithm=cls.name, case=label):
                    algo = cls(data)
                    algo.run_all()
                    self.assertEqual(algo.data, sorted(data))
                    self.assertTrue(algo.finished)

    def test_does_not_modify_input(self):
        for cls in ALGORITHM_CLASSES:
            data = [3, 1, 2]
            cls(data).run_all()
            self.assertEqual(data, [3, 1, 2])

    def test_random_fuzz(self):
        rng = random.Random(99)
        for cls in ALGORITHM_CLASSES:
            for _ in range(60):
                data = [rng.randint(-20, 20) for _ in range(rng.randint(0, 50))]
                algo = cls(data)
                algo.run_all()
                self.assertEqual(algo.data, sorted(data), msg=f"{cls.name}: {data}")

    def test_quick_sort_sorted_input_no_recursion_error(self):
        algo = get_class("quick")(list(range(1500)))   # trường hợp xấu nhất
        algo.run_all()
        self.assertTrue(algo.is_sorted())


class TestStepApi(unittest.TestCase):
    def test_step_by_step_equals_run_all(self):
        data = [random.Random(5).randint(0, 99) for _ in range(40)]
        for cls in ALGORITHM_CLASSES:
            a, b = cls(data), cls(data)
            b.run_all()
            while a.step() is not None:
                pass
            self.assertEqual(a.data, b.data, cls.name)
            self.assertEqual((a.comparisons, a.swaps, a.overwrites, a.steps_count),
                             (b.comparisons, b.swaps, b.overwrites, b.steps_count), cls.name)

    def test_done_emitted_exactly_once(self):
        for cls in ALGORITHM_CLASSES:
            algo = cls([3, 2, 1])
            steps = []
            while True:
                s = algo.step()
                if s is None:
                    break
                steps.append(s)
            self.assertEqual(steps[-1].type, StepType.DONE, cls.name)
            self.assertEqual(sum(s.type is StepType.DONE for s in steps), 1, cls.name)
            self.assertIsNone(algo.step())

    def test_empty_and_single_finish_immediately(self):
        for cls in ALGORITHM_CLASSES:
            for data in ([], [7]):
                algo = cls(data)
                self.assertEqual(algo.step().type, StepType.DONE)
                self.assertIsNone(algo.step())

    def test_step_indices_in_range(self):
        data = [9, 4, 7, 1, 8, 2]
        for cls in ALGORITHM_CLASSES:
            algo = cls(data)
            while (s := algo.step()) is not None:
                self.assertIsInstance(s, Step)
                for idx in s.indices:
                    self.assertTrue(0 <= idx < len(data), f"{cls.name}: {s}")

    def test_reset_restores_initial_state(self):
        data = [5, 2, 9, 1]
        for cls in ALGORITHM_CLASSES:
            algo = cls(data)
            for _ in range(4):
                algo.step()
            algo.reset()
            self.assertEqual(algo.data, data)
            self.assertEqual((algo.comparisons, algo.swaps, algo.overwrites, algo.steps_count), (0, 0, 0, 0))
            self.assertFalse(algo.finished)
            algo.run_all()
            self.assertEqual(algo.data, sorted(data))


class TestCounters(unittest.TestCase):
    def test_bubble_sorted_input_is_linear_and_no_swaps(self):
        n = 50
        algo = get_class("bubble")(list(range(n)))
        algo.run_all()
        self.assertEqual(algo.swaps, 0)
        self.assertEqual(algo.comparisons, n - 1)       # dừng sớm sau 1 lượt

    def test_insertion_sorted_input_is_linear(self):
        n = 50
        algo = get_class("insertion")(list(range(n)))
        algo.run_all()
        self.assertEqual((algo.comparisons, algo.swaps), (n - 1, 0))

    def test_reversed_input_swaps_equal_inversions(self):
        n = 40
        inversions = n * (n - 1) // 2
        for key in ("bubble", "insertion"):
            algo = get_class(key)(list(range(n, 0, -1)))
            algo.run_all()
            self.assertEqual(algo.swaps, inversions, key)

    def test_selection_sort_comparisons_fixed_and_swaps_bounded(self):
        n = 30
        for data in (list(range(n)), list(range(n, 0, -1)),
                     random.Random(2).sample(range(100), n)):
            algo = get_class("selection")(data)
            algo.run_all()
            self.assertEqual(algo.comparisons, n * (n - 1) // 2)
            self.assertLessEqual(algo.swaps, n - 1)

    def test_merge_sort_overwrites_not_swaps(self):
        algo = get_class("merge")(random.Random(3).sample(range(1000), 64))
        algo.run_all()
        self.assertEqual(algo.swaps, 0)
        self.assertGreater(algo.overwrites, 0)
        self.assertLessEqual(algo.comparisons, 64 * 6)     # n log2 n

    def test_comparison_counter_matches_compare_steps(self):
        for cls in ALGORITHM_CLASSES:
            algo = cls(random.Random(4).sample(range(100), 30))
            counts = {t: 0 for t in StepType}
            while (s := algo.step()) is not None:
                counts[s.type] += 1
            self.assertEqual(counts[StepType.COMPARE], algo.comparisons, cls.name)
            self.assertEqual(counts[StepType.SWAP], algo.swaps, cls.name)
            self.assertEqual(counts[StepType.OVERWRITE], algo.overwrites, cls.name)

    def test_n_squared_vs_n_log_n_growth(self):
        rng = random.Random(8)
        small, large = rng.sample(range(10_000), 100), rng.sample(range(10_000), 400)
        ratio = {}
        for key in ("bubble", "merge"):
            a, b = get_class(key)(small), get_class(key)(large)
            a.run_all(); b.run_all()
            ratio[key] = b.comparisons / a.comparisons
        self.assertGreater(ratio["bubble"], 12)    # ~16 lần khi n tăng 4 lần
        self.assertLess(ratio["merge"], 6)         # ~4.6 lần


class TestRegistry(unittest.TestCase):
    def test_names_and_lookup(self):
        self.assertGreaterEqual(len(algorithm_names()), 3)    # yêu cầu đề: >= 3 thuật toán
        self.assertEqual(get_class("Bubble Sort"), get_class("bubble"))
        self.assertIsInstance(create("quick", [2, 1]), SortingAlgorithm)
        with self.assertRaises(KeyError):
            get_class("không tồn tại")

    def test_base_is_abstract(self):
        with self.assertRaises(TypeError):
            SortingAlgorithm([1, 2])

    def test_every_algorithm_has_metadata(self):
        for cls in ALGORITHM_CLASSES:
            self.assertTrue(cls.name and cls.key and cls.description, cls)
            self.assertTrue(cls.time_best and cls.time_average and cls.time_worst and cls.space)


if __name__ == "__main__":
    unittest.main()
