from algorithms.base import SortingAlgorithm

class BubbleSort(SortingAlgorithm):
    """Bubble Sort: mỗi bước so sánh một cặp liền kề, sai thứ tự thì đổi chỗ."""
    def __init__(self, values):
        super().__init__(values)
        self.ten = "Bubble Sort"
        self.i = 0
        self.j = 0

    def step(self):
        n = len(self.values)
        if self.is_done():
            return None

        # 1 buoc = 1 lan so sanh (+ hoan doi neu can)
        self.so_sanh += 1
        idx1, idx2 = self.j, self.j + 1

        if self.values[self.j] > self.values[self.j + 1]:
            self._swap(self.j, self.j + 1)

        self.j += 1
        if self.j >= n - 1 - self.i:
            self.j = 0
            self.i += 1

        return (idx1, idx2)

    def is_done(self):
        return self.i >= len(self.values) - 1

    def reset(self):
        super().reset()
        self.i = 0
        self.j = 0