"""C4 - Lấy dữ liệu (dãy số nguyên) từ một API công khai bằng thư viện requests.

LƯU Ý CHO NHÓM: nguồn API do cả nhóm chọn chung. Trước khi dùng phải đọc điều khoản sử dụng và giới hạn
truy cập của nguồn, rồi ghi tên nguồn vào báo cáo. Nguồn mặc định bên dưới chỉ là gợi ý, cần kiểm tra lại.
Muốn đổi nguồn: sửa API_URL / SOURCE_NAME (hoặc truyền url=, source= khi gọi). Hàm đọc được 2 dạng phản hồi:
mảng JSON [12, 7, ...] hoặc văn bản thuần mỗi số một dòng.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

SOURCE_NAME = "randomnumberapi.com"
API_URL = "https://www.randomnumberapi.com/api/v1.0/random"   # tham số: min, max, count
TIMEOUT_SECONDS = 10
MAX_COUNT = 1000

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
API_DATA_FILE = DATA_DIR / "api_data.json"


class ApiError(Exception):
    """Lỗi khi lấy dữ liệu từ API. str(lỗi) là thông báo rõ ràng để giao diện hiện hộp thoại."""


@dataclass
class FetchResult:
    numbers: list      # danh sách số nguyên đã làm sạch
    removed: int       # số phần tử bị loại (rỗng, sai kiểu, ngoài khoảng)
    source: str
    fetched_at: str
    saved: bool        # đã lưu vào api_data.json chưa

    def message(self):
        text = f"Đã lấy {len(self.numbers)} số từ {self.source}."
        if self.removed:
            text += f" Đã loại {self.removed} phần tử không hợp lệ."
        if not self.saved:
            text += " (Chưa lưu được file api_data.json.)"
        return text


def fetch_numbers(count, min_value, max_value, save=True, url=API_URL, source=SOURCE_NAME):
    """Lấy `count` số nguyên trong [min_value, max_value].

    Trả về FetchResult (dùng .numbers). Raise ValueError nếu tham số sai, ApiError nếu lỗi mạng/dữ liệu.
    """
    _check_args(count, min_value, max_value)

    try:
        response = requests.get(
            url,
            params={"min": min_value, "max": max_value, "count": count},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise ApiError(f"Quá thời gian chờ ({TIMEOUT_SECONDS} giây). Hãy thử lại sau.") from None
    except requests.exceptions.ConnectionError:
        raise ApiError("Không kết nối được tới máy chủ. Hãy kiểm tra kết nối mạng.") from None
    except requests.exceptions.RequestException as e:
        raise ApiError(f"Lỗi khi gửi yêu cầu: {e}") from None

    if response.status_code == 429:
        raise ApiError("Máy chủ báo gửi yêu cầu quá nhiều (HTTP 429). Hãy đợi một lúc rồi thử lại.")
    if response.status_code != 200:
        raise ApiError(f"Máy chủ trả về lỗi HTTP {response.status_code}.")

    items = _extract_items(response)
    numbers, removed = _clean(items, min_value, max_value)
    if not numbers:
        raise ApiError("Dữ liệu nhận về rỗng hoặc không có số hợp lệ nào.")
    numbers = numbers[:count]

    result = FetchResult(numbers, removed, source,
                         datetime.now().isoformat(timespec="seconds"), saved=False)
    if save:
        result.saved = _save(result)
    return result


def _check_args(count, min_value, max_value):
    for name, value in (("count", count), ("min_value", min_value), ("max_value", max_value)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} phải là số nguyên")
    if not 1 <= count <= MAX_COUNT:
        raise ValueError(f"Số lượng cần từ 1 đến {MAX_COUNT}")
    if min_value > max_value:
        raise ValueError("Giá trị nhỏ nhất không được lớn hơn giá trị lớn nhất")


def _extract_items(response):
    """Đọc phản hồi thành danh sách phần tử thô (chưa làm sạch)."""
    try:
        data = response.json()
    except ValueError:      # không phải JSON -> thử văn bản thuần
        data = response.text.split()
    if not isinstance(data, list):
        raise ApiError("Dữ liệu nhận về sai định dạng (cần là một danh sách số).")
    return data


def _clean(items, min_value, max_value):
    """Ép về số nguyên; bỏ rỗng/sai kiểu/ngoài khoảng. Trả về (danh sách số, số phần tử bị loại)."""
    numbers, removed = [], 0
    for item in items:
        value = _to_int(item)
        if value is None or not min_value <= value <= max_value:
            removed += 1
        else:
            numbers.append(value)
    return numbers, removed


def _to_int(item):
    if isinstance(item, bool) or item is None:
        return None
    if isinstance(item, int):
        return item
    if isinstance(item, float):
        return int(item) if item.is_integer() else None
    if isinstance(item, str):
        try:
            return int(item.strip())
        except ValueError:
            return None
    return None


def _save(result, path=None):
    """Lưu api_data.json (tên nguồn, thời điểm lấy, danh sách số). Trả về True nếu thành công."""
    path = Path(path) if path else API_DATA_FILE
    payload = {
        "source": result.source,
        "fetched_at": result.fetched_at,
        "removed": result.removed,
        "numbers": result.numbers,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False    # không lưu được vẫn trả số cho giao diện dùng