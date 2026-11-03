import csv
import json
import os
import tempfile
import unittest

from core import data_manager as dm


class TestGenerate(unittest.TestCase):
    def test_size_and_range(self):
        data = dm.generate(50, "random", low=5, high=20, seed=1)
        self.assertEqual(len(data), 50)
        self.assertTrue(all(5 <= v <= 20 for v in data))

    def test_seed_is_reproducible(self):
        self.assertEqual(dm.generate(30, seed=3), dm.generate(30, seed=3))
        self.assertNotEqual(dm.generate(30, seed=3), dm.generate(30, seed=4))

    def test_scenarios(self):
        s = dm.generate(100, "sorted", seed=1)
        self.assertEqual(s, sorted(s))
        r = dm.generate(100, "reversed", seed=1)
        self.assertEqual(r, sorted(r, reverse=True))
        n = dm.generate(100, "nearly_sorted", seed=1)
        self.assertNotEqual(n, sorted(n))
        inversions = sum(1 for i in range(len(n)) for j in range(i + 1, len(n)) if n[i] > n[j])
        self.assertLess(inversions, 100 * 99 // 4)
        self.assertLessEqual(len(set(dm.generate(200, "few_unique", seed=1))), 5)

    def test_invalid_arguments(self):
        for bad in (0, -1, dm.MAX_ARRAY_SIZE + 1):
            with self.assertRaises(ValueError):
                dm.generate(bad)
        with self.assertRaises(ValueError):
            dm.generate(10, "không_có")
        with self.assertRaises(ValueError):
            dm.generate(10, low=10, high=1)


class TestParse(unittest.TestCase):
    def test_parse_text_separators(self):
        self.assertEqual(dm.parse_text("5, 3 8;1\n-2"), [5, 3, 8, 1, -2])

    def test_parse_text_errors(self):
        for bad in ("", "   ", "1, a, 3", "1.5 2", "1,,x"):
            with self.assertRaises(ValueError, msg=bad):
                dm.parse_text(bad)

    def test_parse_sizes(self):
        self.assertEqual(dm.parse_sizes("500, 100, 100, 50"), [50, 100, 500])
        for bad in ("0", "-5", str(dm.MAX_ARRAY_SIZE + 1), "abc"):
            with self.assertRaises(ValueError, msg=bad):
                dm.parse_sizes(bad)


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_array_roundtrip_json_and_csv(self):
        data = [5, -1, 3, 3, 0, 99]
        for name in ("a.json", "a.csv"):
            dm.save_array(self.path(name), data)
            self.assertEqual(dm.load_array(self.path(name)), data)

    def test_load_json_variants(self):
        with open(self.path("list.json"), "w") as f:
            json.dump([3, 2, 1], f)
        with open(self.path("obj.json"), "w") as f:
            json.dump({"data": [1.0, 2, "3"]}, f)
        self.assertEqual(dm.load_array(self.path("list.json")), [3, 2, 1])
        self.assertEqual(dm.load_array(self.path("obj.json")), [1, 2, 3])

    def test_load_csv_with_header_and_multiple_columns(self):
        with open(self.path("m.csv"), "w", newline="") as f:
            csv.writer(f).writerows([["a", "b"], [1, 2], [3, 4]])
        self.assertEqual(dm.load_array(self.path("m.csv")), [1, 2, 3, 4])

    def test_load_errors(self):
        with open(self.path("bad.json"), "w") as f:
            f.write("{không phải json")
        with open(self.path("text.json"), "w") as f:
            json.dump({"data": [1, "x"]}, f)
        with open(self.path("bad.csv"), "w") as f:
            f.write("value\n1\nabc\n")
        with open(self.path("empty.csv"), "w") as f:
            f.write("value\n")
        with open(self.path("a.txt"), "w") as f:
            f.write("1 2 3")
        for name in ("bad.json", "text.json", "bad.csv", "empty.csv", "a.txt"):
            with self.assertRaises(ValueError, msg=name):
                dm.load_array(self.path(name))
        with self.assertRaises(OSError):
            dm.load_array(self.path("khong_ton_tai.json"))

    def test_save_creates_missing_folder(self):
        p = os.path.join(self.dir, "sub", "dir", "x.json")
        dm.save_array(p, [1, 2])
        self.assertTrue(os.path.exists(p))

    def test_results_roundtrip(self):
        rows = [{"algorithm": "Bubble Sort", "scenario": "random", "size": 100, "repeats": 3,
                 "comparisons": 4950.5, "swaps": 2400.0, "overwrites": 0.0, "steps": 7350.5,
                 "time_ms": 3.141, "correct": True}]
        for name in ("r.json", "r.csv"):
            dm.save_results(self.path(name), rows)
            self.assertEqual(dm.load_results(self.path(name)), rows)

    def test_bundled_sample_files_load(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ("sample.json", "sample.csv", "sample_nearly_sorted.json"):
            self.assertGreaterEqual(len(dm.load_array(os.path.join(root, "data", name))), 2)


if __name__ == "__main__":
    unittest.main()
