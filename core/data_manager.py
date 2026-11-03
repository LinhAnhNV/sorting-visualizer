"""Sinh dữ liệu, nhập tay, đọc/ghi JSON/CSV cho dãy số và kết quả benchmark."""
from __future__ import annotations

import csv
import json
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Sequence

MAX_ARRAY_SIZE = 5000      # giới hạn cho benchmark / nạp file
MAX_VISUAL_SIZE = 500      # giới hạn khi hiển thị hoạt hình trên Canvas

# khoá kịch bản -> nhãn tiếng Việt
SCENARIOS: Dict[str, str] = {
    "random": "Ngẫu nhiên",
    "sorted": "Đã sắp xếp",
    "reversed": "Đảo ngược",
    "nearly_sorted": "Gần như sắp xếp",
    "few_unique": "Ít giá trị khác nhau",
}


# ---------------------------------------------------------------------------
# Sinh dữ liệu
# ---------------------------------------------------------------------------
def generate(n: int, scenario: str = "random", low: int = 1,
             high: Optional[int] = None, seed: Optional[int] = None) -> List[int]:
    """Sinh dãy n số nguyên theo kịch bản.

    scenario: random | sorted | reversed | nearly_sorted | few_unique
    """
    if not isinstance(n, int) or n < 1 or n > MAX_ARRAY_SIZE:
        raise ValueError(f"Kích thước dãy phải là số nguyên từ 1 đến {MAX_ARRAY_SIZE}.")
    if scenario not in SCENARIOS:
        raise ValueError(f"Kịch bản không hợp lệ: {scenario!r}.")
    if high is None:
        high = max(100, 2 * n)
    if high < low:
        raise ValueError("Giá trị lớn nhất phải >= giá trị nhỏ nhất.")

    rng = random.Random(seed)
    if scenario == "few_unique":
        pool = [rng.randint(low, high) for _ in range(5)]
        return [rng.choice(pool) for _ in range(n)]

    data = [rng.randint(low, high) for _ in range(n)]
    if scenario == "sorted":
        data.sort()
    elif scenario == "reversed":
        data.sort(reverse=True)
    elif scenario == "nearly_sorted":
        data.sort()
        swaps = max(1, n // 20) if n >= 2 else 0
        for _ in range(swaps):
            i, j = rng.randrange(n), rng.randrange(n)
            data[i], data[j] = data[j], data[i]
    return data


# ---------------------------------------------------------------------------
# Nhập tay
# ---------------------------------------------------------------------------
def parse_text(text: str) -> List[int]:
    """Chuyển chuỗi như '5, 3 8;1' thành danh sách số nguyên."""
    tokens = [t for t in re.split(r"[,\s;]+", text.strip()) if t]
    if not tokens:
        raise ValueError("Chưa nhập dãy số nào.")
    result: List[int] = []
    for t in tokens:
        try:
            result.append(int(t))
        except ValueError:
            raise ValueError(f"'{t}' không phải là số nguyên hợp lệ.") from None
    _check_size(result)
    return result


def parse_sizes(text: str) -> List[int]:
    """Chuyển '50, 100, 500' thành danh sách kích thước dãy hợp lệ (cho benchmark)."""
    sizes = parse_text(text)
    for s in sizes:
        if s < 1 or s > MAX_ARRAY_SIZE:
            raise ValueError(f"Kích thước {s} nằm ngoài khoảng 1..{MAX_ARRAY_SIZE}.")
    return sorted(set(sizes))


def _check_size(data: Sequence[int]) -> None:
    if len(data) > MAX_ARRAY_SIZE:
        raise ValueError(f"Dãy quá dài ({len(data)} phần tử, tối đa {MAX_ARRAY_SIZE}).")


# ---------------------------------------------------------------------------
# Đọc / ghi dãy số
# ---------------------------------------------------------------------------
def _to_int(value) -> int:
    if isinstance(value, bool):
        raise ValueError("Giá trị logic không phải là số.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return int(value.strip())
    raise ValueError(f"Giá trị {value!r} không phải số nguyên.")


def load_array(path: str) -> List[int]:
    """Đọc dãy số từ file .json hoặc .csv.

    JSON: một danh sách ``[...]`` hoặc đối tượng có khoá ``"data"``.
    CSV : mọi ô số đều được lấy; ô không phải số ở dòng đầu coi là tiêu đề.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            try:
                obj = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"File JSON không hợp lệ: {e}") from None
        if isinstance(obj, dict):
            obj = obj.get("data", obj.get("array"))
        if not isinstance(obj, list):
            raise ValueError("File JSON phải là một danh sách số hoặc có khoá 'data'.")
        try:
            data = [_to_int(v) for v in obj]
        except ValueError as e:
            raise ValueError(f"Dữ liệu JSON không hợp lệ: {e}") from None
    elif ext == ".csv":
        data = []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row_no, row in enumerate(csv.reader(f)):
                for cell in row:
                    cell = cell.strip()
                    if not cell:
                        continue
                    try:
                        data.append(_to_int(cell))
                    except ValueError:
                        if row_no == 0:
                            continue  # tiêu đề cột
                        raise ValueError(
                            f"Dòng {row_no + 1}: '{cell}' không phải số nguyên.") from None
    else:
        raise ValueError("Chỉ hỗ trợ file .json hoặc .csv.")

    if not data:
        raise ValueError("File không chứa số nào.")
    _check_size(data)
    return data


def save_array(path: str, data: Sequence[int]) -> None:
    """Ghi dãy số ra .json hoặc .csv (đuôi file quyết định định dạng)."""
    ext = os.path.splitext(path)[1].lower()
    _ensure_dir(path)
    if ext == ".json":
        with open(path, "w", encoding="utf-8") as f:
            # dãy số nằm trên một dòng cho gọn, dễ đọc bằng mắt
            f.write('{\n  "size": %d,\n  "data": %s\n}\n' % (len(data), json.dumps(list(data))))
    elif ext == ".csv":
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["value"])
            for v in data:
                w.writerow([v])
    else:
        raise ValueError("Chỉ hỗ trợ ghi file .json hoặc .csv.")


# ---------------------------------------------------------------------------
# Đọc / ghi kết quả benchmark
# ---------------------------------------------------------------------------
RESULT_FIELDS = ["algorithm", "scenario", "size", "repeats", "comparisons",
                 "swaps", "overwrites", "steps", "time_ms", "correct"]


def save_results(path: str, rows: List[dict]) -> None:
    ext = os.path.splitext(path)[1].lower()
    _ensure_dir(path)
    if ext == ".json":
        payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
                   "results": rows}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    elif ext == ".csv":
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=RESULT_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    else:
        raise ValueError("Chỉ hỗ trợ ghi file .json hoặc .csv.")


def load_results(path: str) -> List[dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["results"]
    if ext == ".csv":
        rows = []
        with open(path, "r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                for k in ("size", "repeats"):
                    r[k] = int(r[k])
                for k in ("comparisons", "swaps", "overwrites", "steps", "time_ms"):
                    r[k] = float(r[k])
                r["correct"] = r["correct"] in ("True", "true", "1")
                rows.append(r)
        return rows
    raise ValueError("Chỉ hỗ trợ đọc file .json hoặc .csv.")


def default_results_path(results_dir: str, ext: str = ".json") -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(results_dir, f"benchmark_{stamp}{ext}")


def _ensure_dir(path: str) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
