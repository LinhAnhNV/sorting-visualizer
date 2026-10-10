# Lớp cơ sở cho các thuật toán sắp xếp chạy từng bước (module A).
from abc import ABC, abstractmethod

class SortingAlgorithm(ABC):
    """Khuôn chung cho mọi thuật toán sắp xếp."""
    def __init__(self, values):
        self._original = list(values)  # bản gốc, để reset() quay về
        self.values = list(values)     # bản đang được sắp xếp dần
        self.so_sanh = 0               # số lần so sánh
        self.so_hoan_doi = 0           # số lần hoán đổi
        self.ten = "Chua dat ten"      # lớp con gán lại tên thật

    @abstractmethod
    def step(self):
        """Làm đúng một thao tác nhỏ (một lần so sánh hoặc hoán đổi).
        Trả về (idx1, idx2): hai vị trí vừa xử lý, để Canvas tô màu.
        Trả về None nếu thuật toán đã xong."""

    @abstractmethod
    def is_done(self):
        """True nếu đã sắp xếp xong.
        Phải đúng cả với dãy rỗng và dãy 1 phần tử, nếu không run_all()
        sẽ chạy mãi không dừng."""

    def get_state(self):
        """Trả về bản sao dãy hiện tại để Canvas vẽ."""
        return self.values

    def get_counts(self):
        """Trả về (số lần so sánh, số lần hoán đổi)."""
        return self.so_sanh, self.so_hoan_doi

    def get_ten(self):
        """Trả về tên thuật toán để hiển thị."""
        return self.ten

    def reset(self):
        """Đưa dãy về ban đầu và xóa bộ đếm.
        Lớp con có biến nhớ vị trí riêng (VD i, j) thì ghi đè hàm này,
        gọi super().reset() rồi tự đặt lại các biến đó."""
        self.values = list(self._original)
        self.so_sanh = 0
        self.so_hoan_doi = 0

    def run_all(self):
        """Chạy liên tục tới khi xong, trả về (so_sanh, so_hoan_doi)."""
        while not self.is_done():
            self.step()
        return self.get_counts

    def _swap(self, i, j):
        """Hoán đổi hai phần tử và tự cộng vào bộ đếm hoán đổi."""
        self.values[i], self.values[j] = self.values[j], self.values[i]
        self.so_hoan_doi += 1