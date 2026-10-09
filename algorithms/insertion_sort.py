from algorithms.base import SortingAlgorithm

class InsertionSort(SortingAlgorithm):
    """Lấy từng phần tử, lùi dần sang trái cho tới đúng chỗ."""
    def __init__(self, values):
        super().__init__(values)
        self.ten = "Insertion sort"
        self.i = 1  # phần tử đang được chèn; bên trái i là phần đã sắp xếp
        self.j = 1  # vị trí hiện tại của phần tử đó khi đang lùi sang trái

    def step(self):
        if self.is_done():
            return None

        # 1 bước = đúng 1 lần so sánh phần tử với phần tử đứng trước nó
        a, b = self.j - 1, self.j
        self.so_sanh += 1

        if self.values[a] > self.values[b]:
            self._swap(a, b)
            self.j -= 1
            if self.j == 0:
                self._next_element()
        else:
            self._next_element()
        
        return (a, b)

    def _next_element(self):
        """Chuyển sang phần tử kế tiếp cần chèn."""
        self.i += 1
        self.j = self.i

    def is_done(self):
        """i chạy hết dãy là xong; dãy rỗng / 1 phần tử xong ngay"""
        return self.i >= len(self.values)

    def reset(self):
        super().reset()
        self.i = 1
        self.j = 0