from algorithms.base import SortingAlgorithm

class BubbleSort(SortingAlgorithm):
    """Mỗi bước so sánh một cặp liền kề, sai thứ tự thì đổi chỗ."""
    def __init__(self, values):
        super().__init__(values)
        self.name = "Bubble Sort"
        self.i = 0  # số lượt đã chạy xong; cuối dãy có i phần tử đã về đúng chỗ
        self.j = 0  # vị trí cặp đang so sánh trong lượt hiện tại

    def step(self):
        if self.is_done():
            return None

        # 1 bước = đúng 1 lần so sánh 2 phần tử kề nhau (+ đổi chỗ nếu cần)
        a, b = self.j, self.j + 1
        self.so_sanh += 1

        if self.values[a] > self.values[b]:
            self._swap(a, b)

        self.j += 1
        if self.j >= len(self.values) - 1 - self.i:  # hết lượt: sang lượt mới
            self._next_pass()

        return (a, b)

    def _next_pass(self):
        self.j = 0
        self.i += 1

    def is_done(self):
        return self.i >= len(self.values) - 1

    def reset(self):
        super().reset()
        self.i = 0
        self.j = 0