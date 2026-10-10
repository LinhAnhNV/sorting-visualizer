# So sánh hiệu năng các thuật toán sắp xếp trên nhiều kích thước dãy (module A)
import random
import time
from algorithms.bubble_sort import BubbleSort
from algorithms.insertion_sort import InsertionSort
from algorithms.selection_sort import SelectionSort

# Danh sách các LỚP thuật toán (chưa tạo object) để duyệt bằng vòng lặp.
# Thêm thuật toán mới chỉ cần thêm vào đây.
ALGORITHMS = [BubbleSort, InsertionSort, SelectionSort]

def benchmark(sizes, seed=None):
    """Chạy từng thuật toán trên cùng một dãy ngẫu nhiên cho mỗi kích thước.
 
    sizes: danh sách kích thước, VD [10, 50, 100].
    seed:  số nguyên để dãy ngẫu nhiên lặp lại được (dùng khi kiểm thử).
 
    Trả về danh sách dict, mỗi dict là một thuật toán ở một kích thước:
    {"algorithm", "size", "comparisons", "swaps", "time_ms"}"""
    for size in sizes:
        if not isinstance(size, int) or size < 0:
            raise ValueError(f"Lỗi: Kích thước dãy phải là số nguyên không âm, nhận được: {size!r}")

    rng = random.Random(seed)  # bộ sinh riêng, không ảnh hưởng random chung
    result = []

    for size in sizes:
        values = [rng.randint(1, 1000) for _ in range(size)]
        for algo_class in ALGORITHMS:
            """Mọi thuật toán nhận cùng một dãy; lớp cha tự sao chép nên
            thuật toán này không làm hỏng dãy của thuật toán khác."""
            algo = algo_class(values)

            start = time.perf_counter()
            comparisons, swaps = algo.run_all()
            elapsed_ms = (time.perf_counter() - start) * 1000

            result.append({
                "algorithm": algo.get_name(),
                "size": size,
                "comparisons": comparisons,
                "swaps": swaps,
                "time_ms": round(elapsed_ms, 3),
            })
    return result