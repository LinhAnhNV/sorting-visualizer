from algorithms.base import SortingAlgorithm

class SelectionSort(SortingAlgorithm):
    """Mỗi lượt tìm phần tử nhỏ nhất của phần chưa xếp,
    rồi đổi chỗ nó về đầu phần đó."""
    def __init__(self, values):
        super().__init__(values)
        self.name = "Selection Sort"
        self.i = 0          # vị trí đang chờ phần tử nhỏ nhất; bên trái i đã xong
        self.j = 1          # vị trí đang xét trong lượt hiện tại
        self.min_idx = 0    # vị trí phần tử nhỏ nhất tìm được tới lúc này

    def step(self):
        if self.is_done():
            return None

        # 1 bước = đúng 1 lần so sánh phần tử thứ j với phần tử nhỏ nhất đang giữ
        a, b = self.min_idx, self.j
        self.so_sanh += 1
        if self.values[b] < self.values[a]:
            self.min_idx = b

        self.j += 1
        if self.j >= len(self.values):  # hết lượt: đổi chỗ rồi sang lượt mới
            if self.min_idx != self.i:
                self._swap(self.i, self.min_idx)
            self._next_pass()

        return (a, b)

    def _next_pass(self):
        """Bắt đầu lượt mới cho vị trí kế tiếp."""
        self.i += 1
        self.j= self.i + 1
        self.min_idx = self.i

    def is_done(self):
        """i chạy tới phần tử áp chót là xong; dãy rỗng / 1 phần tử xong ngay"""
        return self.i >= len(self.values) - 1

    def reset(self):
        super().reset()
        self.i = 0
        self.j = 0
        self.min_idx = 0