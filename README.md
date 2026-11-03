# Hệ thống trực quan hóa thuật toán sắp xếp (Đề tài 28)

Ứng dụng **Tkinter** minh họa quá trình chạy của 5 thuật toán sắp xếp trên **Canvas**, có chạy từng bước,
tạm dừng/tiếp tục, đếm số lần so sánh – hoán đổi, và so sánh hiệu năng trên nhiều kích thước dãy.
Chỉ dùng thư viện chuẩn của Python.

## Chạy nhanh

```bash
python main.py                # mở giao diện
python main.py --benchmark    # benchmark dòng lệnh, lưu kết quả vào data/results/
python -m unittest discover -s tests -t .    # chạy toàn bộ 85 test
```

Yêu cầu: Python 3.8+ (khuyến nghị 3.10+) và `tkinter`
(Windows/macOS có sẵn; Ubuntu/Debian: `sudo apt install python3-tk`).

## Cấu trúc

```
sorting_visualizer/
├── main.py                  # điểm vào (GUI hoặc --benchmark)
├── algorithms/              # lớp trừu tượng SortingAlgorithm + 5 thuật toán
│   ├── base.py  bubble.py  selection.py  insertion.py  merge.py  quick.py
├── core/                    # logic không phụ thuộc giao diện
│   ├── data_manager.py      # sinh số, nhập tay, đọc/ghi JSON/CSV
│   ├── runner.py            # máy trạng thái IDLE/RUNNING/PAUSED/FINISHED
│   └── benchmark.py         # đo hiệu năng nhiều kích thước
├── ui/                      # giao diện Tkinter
│   ├── app.py  canvas_view.py  control_panel.py  benchmark_window.py
├── tests/                   # 85 test (unittest)
├── data/                    # sample.json, sample.csv, results/ (kết quả benchmark)
└── docs/                    # BaoCao.md, HuongDanSuDung.md
```

## Tài liệu

* [`docs/BaoCao.md`](docs/BaoCao.md) – báo cáo phân tích, thiết kế lớp, kiểm thử, kết quả đo.
* [`docs/HuongDanSuDung.md`](docs/HuongDanSuDung.md) – hướng dẫn sử dụng.
