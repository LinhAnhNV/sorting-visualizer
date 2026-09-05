"""
DEMO: Minh hoa y tuong SortingAlgorithm + Canvas + Control panel
Chi lam Bubble Sort de de theo doi. Day la ban demo don gian,
chua theo dung cau truc thu muc (algorithms/, sessions/...) da thiet ke.
"""

import tkinter as tk
from abc import ABC, abstractmethod
import random

# ============================================================
# PHAN 1: Lop truu tuong (kien thuc Chuong 2 - OOP)
# Neu chua hoc toi day, cu doc nhu 1 "khuon mau" chung cho moi thuat toan
# ============================================================
class SortingAlgorithm(ABC):
    def __init__(self, values):
        self.values = values.copy()
        self.so_sanh = 0
        self.so_hoan_doi = 0
        self.ten = "Chua dat ten"

    @abstractmethod
    def step(self):
        """Thuc hien 1 buoc nho nhat. Tra ve (idx1, idx2) dang duoc so sanh
        de Canvas biet highlight cot nao, hoac None neu da xong."""
        pass

    def get_state(self):
        return self.values

    def is_done(self):
        return self.so_sanh > 0 and getattr(self, "_done", False)

    def get_counts(self):
        return self.so_sanh, self.so_hoan_doi

    def get_ten(self):
        return self.ten


# ============================================================
# PHAN 2: Lop con - Bubble Sort
# ============================================================
class BubbleSort(SortingAlgorithm):
    def __init__(self, values):
        super().__init__(values)
        self.ten = "Bubble Sort"
        self.i = 0
        self.j = 0
        self._done = False

    def step(self):
        n = len(self.values)
        if self.i >= n - 1:
            self._done = True
            return None

        # 1 buoc = 1 lan so sanh (+ hoan doi neu can)
        self.so_sanh += 1
        idx1, idx2 = self.j, self.j + 1

        if self.values[self.j] > self.values[self.j + 1]:
            self.values[self.j], self.values[self.j + 1] = (
                self.values[self.j + 1],
                self.values[self.j],
            )
            self.so_hoan_doi += 1

        self.j += 1
        if self.j >= n - 1 - self.i:
            self.j = 0
            self.i += 1

        return (idx1, idx2)


# ============================================================
# PHAN 3: Giao dien Tkinter (kien thuc Chuong 4)
# ============================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Demo - Bubble Sort Visualizer")

        self.values = [random.randint(10, 100) for _ in range(9)]
        self.algo = BubbleSort(self.values)
        self.running = False
        self.highlight = None

        # --- Canvas ve cot ---
        self.canvas = tk.Canvas(root, width=400, height=200, bg="white")
        self.canvas.pack(pady=10)

        # --- Control panel ---
        frame = tk.Frame(root)
        frame.pack(pady=5)

        tk.Button(frame, text="Random", command=self.lam_moi).grid(row=0, column=0, padx=3)
        tk.Button(frame, text="Start", command=self.start).grid(row=0, column=1, padx=3)
        tk.Button(frame, text="Pause", command=self.pause).grid(row=0, column=2, padx=3)
        tk.Button(frame, text="Step", command=self.step_once).grid(row=0, column=3, padx=3)
        tk.Button(frame, text="Reset", command=self.reset).grid(row=0, column=4, padx=3)

        # --- Slider toc do ---
        self.toc_do = tk.Scale(root, from_=1, to=10, orient="horizontal", label="Toc do")
        self.toc_do.set(5)
        self.toc_do.pack(pady=5)

        # --- Label dem so sanh/hoan doi ---
        self.label_dem = tk.Label(root, text="So sanh: 0 | Hoan doi: 0")
        self.label_dem.pack(pady=5)

        self.ve_canvas()

    def ve_canvas(self):
        self.canvas.delete("all")
        n = len(self.algo.values)
        w = 400 // n
        for idx, val in enumerate(self.algo.values):
            x0 = idx * w
            y0 = 200 - val
            x1 = x0 + w - 4
            y1 = 200
            # cot dang duoc so sanh thi to mau cam, con lai mau xam
            mau = "orange" if self.highlight and idx in self.highlight else "gray"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=mau)

        so_sanh, so_hoan_doi = self.algo.get_counts()
        self.label_dem.config(text=f"So sanh: {so_sanh} | Hoan doi: {so_hoan_doi}")

    def step_once(self):
        if self.algo.is_done():
            self.running = False
            return
        self.highlight = self.algo.step()
        self.ve_canvas()

    def vong_lap_tu_dong(self):
        if not self.running:
            return
        if self.algo.is_done():
            self.running = False
            return
        self.step_once()
        # .after(ms, ham) = goi lai ham nay sau vai mili-giay
        # toc do cao -> cho it thoi gian hon
        delay = 600 - self.toc_do.get() * 50
        self.root.after(delay, self.vong_lap_tu_dong)

    def start(self):
        if not self.running:
            self.running = True
            self.vong_lap_tu_dong()

    def pause(self):
        self.running = False

    def reset(self):
        self.running = False
        self.algo = BubbleSort(self.values)
        self.highlight = None
        self.ve_canvas()

    def lam_moi(self):
        self.running = False
        self.values = [random.randint(10, 100) for _ in range(9)]
        self.algo = BubbleSort(self.values)
        self.highlight = None
        self.ve_canvas()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()