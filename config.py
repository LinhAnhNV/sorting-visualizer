"""Hằng số dùng chung cho cả nhóm. Mọi module lấy giá trị từ đây."""
 
# ---- Giao diện mô phỏng sắp xếp (module A) ----
MAX_ELEMENTS = 30       # số phần tử tối đa của dãy
RANDOM_SIZE = 12        # số phần tử khi bấm nút Random
RANDOM_MIN = 5          # giá trị nhỏ nhất khi sinh ngẫu nhiên
RANDOM_MAX = 99         # giá trị lớn nhất khi sinh ngẫu nhiên

CANVAS_WIDTH = 480      # kích thước ban đầu của Canvas (sẽ co giãn theo cửa sổ)
CANVAS_HEIGHT = 240
CANVAS_BG = "white"

COLOR_BAR = "#8a8f98"       # cột bình thường
COLOR_COMPARE = "#f0a030"   # cặp cột đang được so sánh
COLOR_DONE = "#3da35d"      # cột khi đã sắp xếp xong
 
DEFAULT_SPEED = 5       # tốc độ ban đầu của thanh trượt (1 chậm, 10 nhanh)