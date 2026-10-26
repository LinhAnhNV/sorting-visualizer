"""Panel quản lý lịch sử session (chỉ dùng widget tkinter thuần, không dùng ttk).

Cách phần code sắp xếp (của người khác) đưa dữ liệu vào panel:
    panel = SessionPanel(root, manager, result_provider=ham_lay_ket_qua)
    # hoặc gắn sau: panel.set_result_provider(ham_lay_ket_qua)

`ham_lay_ket_qua()` không nhận tham số và trả về kết quả của lần sắp xếp gần nhất:
    {"values": [5, 2, 9],          # dãy đầu vào
     "sorted_values": [2, 5, 9],   # dãy sau khi sắp xếp
     "swaps": 2,                   # số lần hoán đổi
     "comparisons": 3}             # số lần so sánh
hoặc trả về None nếu chưa có kết quả nào. Khi bấm "Thêm session", người dùng chỉ chọn
thuật toán và nhập ghi chú; mã session (SE0001, SE0002...) do hệ thống tự sinh.

Không dùng giao diện thì gọi thẳng:
    manager.add_and_save(algorithm, values, sorted_values, swaps, comparisons, note)
"""
import os
import random
import sys
import tkinter as tk
from collections.abc import Mapping
from datetime import datetime
from tkinter import filedialog, messagebox

import session_manager
import stats
import ui_compare_canvas

ALGORITHMS = ["Bubble Sort", "Selection Sort", "Insertion Sort"]
ALL = "Tất cả"  # lựa chọn "không lọc"

# Các khóa bắt buộc trong kết quả sắp xếp mà phần code sắp xếp phải cung cấp
RESULT_KEYS = ("values", "sorted_values", "swaps", "comparisons")

# Các cột của bảng: (khóa, tiêu đề, độ rộng tính theo ký tự, căn lề "<" trái / ">" phải)
COLUMNS = (
    ("id", "ID", 8, "<"),
    ("user", "User", 10, "<"),
    ("algorithm", "Thuật toán", 15, "<"),
    ("size", "Số phần tử", 10, ">"),
    ("swaps", "Swaps", 7, ">"),
    ("comparisons", "So sánh", 8, ">"),
    ("time", "Thời gian", 19, "<"),
    ("note", "Ghi chú", 24, "<"),
)
TABLE_FONT = "TkFixedFont"  # font cách đều để các cột thẳng hàng
GRAY = "gray"


def demo_result_provider():
    """CHỈ ĐỂ CHẠY THỬ giao diện (python ui_session_panel.py Nhu --demo): sinh một dãy ngẫu nhiên,
    sắp xếp nổi bọt và đếm swap/so sánh. Trong ứng dụng thật, dữ liệu này do phần code sắp xếp cung cấp."""
    values = [random.randint(1, 99) for _ in range(random.randint(5, 10))]
    data = list(values)
    swaps = comparisons = 0
    for i in range(len(data) - 1):
        for j in range(len(data) - 1 - i):
            comparisons += 1
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
                swaps += 1
    return {"values": values, "sorted_values": data, "swaps": swaps, "comparisons": comparisons}


def show_warnings(manager):
    """Hiện các cảnh báo của lần load gần nhất (bản ghi lỗi bị bỏ qua, file chưa tồn tại...)."""
    if not manager.warnings:
        return
    shown = manager.warnings[:8]
    text = "\n".join(f"- {w}" for w in shown)
    if len(manager.warnings) > len(shown):
        text += f"\n... và {len(manager.warnings) - len(shown)} cảnh báo khác"
    messagebox.showwarning("Cảnh báo dữ liệu", text)


def format_row(values):
    """Ghép một dòng của bảng từ dict {khóa cột: giá trị}; ô quá dài được cắt bớt và thêm dấu …"""
    cells = []
    for key, _title, width, align in COLUMNS:
        text = str(values[key])
        if len(text) > width:
            text = text[:width - 1] + "…"
        cells.append(f"{text:{align}{width}}")
    return "  ".join(cells)


class AddSessionDialog(tk.Toplevel):
    """Hộp thoại thêm session: người dùng chỉ chọn thuật toán và nhập ghi chú.
    Dãy số, dãy sau sắp xếp, swaps, comparisons lấy từ `result` (do phần code sắp xếp cung cấp)."""

    def __init__(self, master, manager, result, on_added):
        super().__init__(master)
        self.title("Thêm session")
        self.resizable(False, False)
        self.manager = manager
        self.result = result
        self.on_added = on_added

        self.algorithm = tk.StringVar(value=ALGORITHMS[0])
        self.note = tk.StringVar()

        form = tk.Frame(self, padx=12, pady=12)
        form.pack()

        # Tóm tắt dữ liệu sắp được lưu (chỉ đọc) để người dùng biết mình đang lưu kết quả nào
        summary = (f"Kết quả sắp xếp sẽ được lưu: {len(result['values'])} phần tử, "
                   f"{result['swaps']} swaps, {result['comparisons']} so sánh")
        tk.Label(form, text=summary, fg=GRAY).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        tk.Label(form, text="Thuật toán").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        algorithm_menu = tk.OptionMenu(form, self.algorithm, *ALGORITHMS)
        algorithm_menu.config(width=30, anchor="w")
        algorithm_menu.grid(row=1, column=1, sticky="w", pady=4)

        tk.Label(form, text="Ghi chú").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        tk.Entry(form, textvariable=self.note, width=36).grid(row=2, column=1, sticky="w", pady=4)

        buttons = tk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        tk.Button(buttons, text="Lưu", width=8, command=self.submit).pack(side="left", padx=4)
        tk.Button(buttons, text="Hủy", width=8, command=self.destroy).pack(side="left", padx=4)

        self.transient(master)
        self.grab_set()

    def submit(self):
        try:
            self.manager.add_and_save(
                self.algorithm.get(),
                self.result["values"], self.result["sorted_values"],
                self.result["swaps"], self.result["comparisons"],
                self.note.get())
        except ValueError as e:
            messagebox.showerror("Dữ liệu sắp xếp không hợp lệ", str(e), parent=self)
            return
        except session_manager.SessionDataError as e:
            messagebox.showerror("Không lưu được", str(e), parent=self)
            return

        self.on_added()
        self.destroy()


class SessionPanel(tk.Frame):
    def __init__(self, master, manager, result_provider=None):
        super().__init__(master, padx=8, pady=8)
        self.manager = manager
        self.result_provider = result_provider  # hàm lấy kết quả sắp xếp từ code của người khác
        self._shown = []          # các Session đang hiển thị, đúng thứ tự từng dòng của bảng
        self._compare_window = None
        self._build()
        self.refresh()

    def _build(self):
        # Thanh chọn user: người khác nhập tên của mình rồi bấm "Đổi user"
        user_bar = tk.Frame(self)
        user_bar.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        tk.Label(user_bar, text="User:").pack(side="left")
        self.user_var = tk.StringVar(value=self.manager.username)
        user_entry = tk.Entry(user_bar, textvariable=self.user_var, width=20)
        user_entry.pack(side="left", padx=6)
        user_entry.bind("<Return>", lambda _e: self.switch_user())
        tk.Button(user_bar, text="Đổi user", command=self.switch_user).pack(side="left")
        self.role_label = tk.Label(user_bar, fg=GRAY)
        self.role_label.pack(side="left", padx=12)

        # Thanh lọc / phạm vi xem
        tools_bar = tk.Frame(self)
        tools_bar.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(tools_bar, text="Lọc thuật toán:").pack(side="left")
        self.filter_var = tk.StringVar(value=ALL)
        self.filter_box = tk.OptionMenu(tools_bar, self.filter_var, ALL)
        self.filter_box.config(width=14, anchor="w")
        self.filter_box.pack(side="left", padx=6)
        self._set_filter_options([ALL] + ALGORITHMS)

        # Chỉ admin mới bật được ô này
        self.view_all = tk.BooleanVar(value=False)
        self.view_all_check = tk.Checkbutton(tools_bar, text="Xem tất cả user (admin)",
                                             variable=self.view_all, command=self.refresh)
        self.view_all_check.pack(side="left", padx=(20, 0))

        # Bảng danh sách session: dòng tiêu đề + Listbox, cùng font cách đều để cột thẳng hàng
        tk.Label(self, text=format_row({key: title for key, title, _w, _a in COLUMNS}),
                 font=TABLE_FONT, anchor="w", justify="left").grid(row=2, column=0, sticky="ew")
        total_width = sum(w for _k, _t, w, _a in COLUMNS) + 2 * (len(COLUMNS) - 1)
        self.listbox = tk.Listbox(self, font=TABLE_FONT, width=total_width, height=10,
                                  selectmode="browse", exportselection=False, activestyle="none")
        scroll = tk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scroll.set)
        self.listbox.grid(row=3, column=0, sticky="nsew")
        scroll.grid(row=3, column=1, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Chi tiết session đang chọn
        self.detail = tk.Text(self, height=4, state="disabled", wrap="word")
        self.detail.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Nút chức năng
        buttons = tk.Frame(self)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=8)
        tk.Button(buttons, text="So sánh thuật toán", command=self.open_compare).pack(side="left", padx=4)
        tk.Button(buttons, text="Xuất thống kê", command=self.export_stats).pack(side="left", padx=4)
        tk.Button(buttons, text="Thêm session", command=self.add_session).pack(side="left", padx=4)
        tk.Button(buttons, text="Làm mới", command=self.reload).pack(side="left", padx=4)
        tk.Button(buttons, text="Xóa session", command=self.delete_selected).pack(side="left", padx=4)

        # Thống kê
        self.stats_label = tk.Label(self, justify="left", anchor="w")
        self.stats_label.grid(row=6, column=0, columnspan=2, sticky="w")

        # Cho biết đang đọc file nào, có bao nhiêu session
        self.status_label = tk.Label(self, fg=GRAY, justify="left", anchor="w")
        self.status_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

    # ---------- dữ liệu đang hiển thị ----------
    def _viewing_all(self):
        return self.manager.is_admin and self.view_all.get()

    def _base_sessions(self):
        """Session trước khi lọc thuật toán: của mình, hoặc của tất cả nếu là admin đang bật xem tất cả."""
        if self._viewing_all():
            try:
                return self.manager.all_sessions()
            except session_manager.SessionDataError as e:
                self.view_all.set(False)  # quay về chỉ xem session của mình
                messagebox.showerror("Lỗi file dữ liệu",
                                     f"Không đọc được session của các user khác:\n{e}")
        return self.manager.sessions

    def _scope_text(self):
        return "tất cả người dùng" if self._viewing_all() else f"user {self.manager.username}"

    def _set_filter_options(self, options):
        """Dựng lại menu lọc (OptionMenu không tự cập nhật khi danh sách lựa chọn thay đổi)."""
        menu = self.filter_box["menu"]
        menu.delete(0, "end")
        for option in options:
            menu.add_command(label=option, command=lambda value=option: self._choose_filter(value))

    def _choose_filter(self, value):
        self.filter_var.set(value)
        self.refresh()

    def _update_filter_options(self, base):
        """Danh sách lọc = các thuật toán có sẵn + thuật toán lạ xuất hiện trong dữ liệu."""
        extra = sorted({s.algorithm for s in base} - set(ALGORITHMS))
        options = [ALL] + ALGORITHMS + extra
        self._set_filter_options(options)
        if self.filter_var.get() not in options:
            self.filter_var.set(ALL)

    def refresh(self):
        """Vẽ lại bảng và thống kê theo vai trò, phạm vi xem và bộ lọc hiện tại."""
        # Không phải admin thì không được bật chế độ xem tất cả
        if not self.manager.is_admin:
            self.view_all.set(False)
        self.view_all_check.config(state="normal" if self.manager.is_admin else "disabled")
        self.role_label.config(text=f"Vai trò: {self.manager.role}")

        base = self._base_sessions()
        self._update_filter_options(base)
        selected_algorithm = self.filter_var.get()
        shown = self.manager.filter_by_algorithm(
            None if selected_algorithm == ALL else selected_algorithm, sessions=base)

        self.listbox.delete(0, "end")
        self._shown = list(shown)
        for s in self._shown:
            self.listbox.insert("end", format_row({
                "id": s.session_id, "user": s.username, "algorithm": s.algorithm,
                "size": len(s.values), "swaps": s.swaps, "comparisons": s.comparisons,
                "time": s.create_at.replace("T", " "), "note": s.note,
            }))
        self._set_detail("")
        self.stats_label.config(text=stats.format_report(shown))

        path = self.manager.data_file
        if os.path.exists(path):
            warn = f" | Cảnh báo: {len(self.manager.warnings)}" if self.manager.warnings else ""
            self.status_label.config(
                text=f"User '{self.manager.username}' ({self.manager.role}) | Phạm vi: {self._scope_text()}"
                     f" | Hiển thị {len(shown)}/{len(base)} session{warn} | File: {path}")
        else:
            self.status_label.config(text=f"Không tìm thấy file dữ liệu: {path} (sẽ được tạo khi lưu)")

        self.winfo_toplevel().title(f"Lịch sử session - {self.manager.username}")

    # ---------- đọc dữ liệu, xử lý lỗi file ----------
    def _try_load(self, manager):
        """Load dữ liệu cho manager, xử lý mọi lỗi file. Trả về True nếu load thành công."""
        try:
            manager.load()
        except session_manager.CorruptDataError as e:
            # File hỏng: hỏi người dùng có muốn sao lưu và tạo file mới không (không tự ý ghi đè)
            if not messagebox.askyesno(
                    "File dữ liệu bị lỗi",
                    f"{e}\n\nSao lưu file lỗi và tạo file dữ liệu mới (trống)?\n"
                    f"Dữ liệu của tất cả user sẽ nằm trong bản sao lưu, bạn có thể sửa tay rồi khôi phục."):
                return False
            try:
                backup = manager.reset_data_file()
                manager.load()
            except session_manager.SessionDataError as e2:
                messagebox.showerror("Lỗi file dữ liệu", str(e2))
                return False
            if backup:
                messagebox.showinfo("Đã xử lý", f"File lỗi được sao lưu tại:\n{backup}\n\nĐã tạo file dữ liệu mới.")
        except session_manager.SessionDataError as e:
            messagebox.showerror("Lỗi file dữ liệu", str(e))
            return False

        show_warnings(manager)
        return True

    def reload(self):
        """Đọc lại dữ liệu từ file rồi vẽ lại."""
        if self._try_load(self.manager):
            self.refresh()

    def switch_user(self):
        name = self.user_var.get().strip()
        if not name:
            messagebox.showinfo("Thông báo", "Hãy nhập tên user.")
            return
        new_manager = session_manager.SessionManager(name, data_file=self.manager.data_file)
        if not self._try_load(new_manager):
            self.user_var.set(self.manager.username)  # giữ nguyên user hiện tại
            return
        self.manager = new_manager
        self.view_all.set(False)  # đổi user thì quay về xem session của riêng mình
        self.refresh()

    def set_result_provider(self, provider):
        """Gắn (hoặc đổi) hàm cung cấp kết quả sắp xếp, xem mô tả ở đầu file."""
        self.result_provider = provider

    def _fetch_result(self):
        """Lấy kết quả sắp xếp từ phần code sắp xếp. Trả về dict hợp lệ, hoặc None (đã báo cho người dùng)."""
        if self.result_provider is None:
            messagebox.showinfo("Chưa có dữ liệu",
                                "Panel chưa được kết nối với phần sắp xếp nên chưa có kết quả để lưu.")
            return None
        try:
            result = self.result_provider()
        except Exception as e:  # code bên ngoài có thể lỗi bất kỳ, không để làm sập giao diện
            messagebox.showerror("Lỗi", f"Không lấy được kết quả sắp xếp:\n{e}")
            return None
        if not result:
            messagebox.showinfo("Chưa có kết quả",
                                "Chưa có kết quả sắp xếp nào. Hãy chạy sắp xếp trước rồi thêm session.")
            return None
        if not isinstance(result, Mapping):
            messagebox.showerror("Lỗi", "Kết quả sắp xếp phải là dict (xem mô tả ở đầu file ui_session_panel.py).")
            return None
        missing = [key for key in RESULT_KEYS if key not in result]
        if missing:
            messagebox.showerror("Lỗi", f"Kết quả sắp xếp thiếu: {', '.join(missing)}")
            return None
        return result

    def add_session(self):
        result = self._fetch_result()
        if result is None:
            return
        AddSessionDialog(self, self.manager, result, on_added=self.refresh)

    def open_compare(self):
        # Chỉ mở một cửa sổ so sánh, nếu đã mở thì đưa lên trước
        if self._compare_window is not None and self._compare_window.winfo_exists():
            self._compare_window.lift()
            self._compare_window.redraw()
            return
        self._compare_window = ui_compare_canvas.CompareWindow(
            self, lambda: (self._base_sessions(), self._scope_text()))

    def export_stats(self):
        """Xuất thống kê của các session đang hiển thị (theo phạm vi xem và bộ lọc) ra file JSON."""
        if not self._shown:
            messagebox.showinfo("Thông báo", "Không có session nào để thống kê.")
            return

        default_name = f"thong_ke_{self.manager.username}_{datetime.now():%Y%m%d_%H%M%S}.json"
        path = filedialog.asksaveasfilename(
            title="Xuất thống kê ra file JSON", defaultextension=".json", initialfile=default_name,
            filetypes=[("File JSON", "*.json"), ("Tất cả các file", "*.*")])
        if not path:  # người dùng bấm Hủy
            return

        # Không cho ghi đè lên chính file dữ liệu session
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(self.manager.data_file)):
            messagebox.showerror("Không xuất được",
                                 "Không thể ghi đè file dữ liệu session. Hãy chọn tên file khác.")
            return

        selected = self.filter_var.get()
        try:
            stats.export_json(self._shown, path, username=self.manager.username,
                              scope=self._scope_text(),
                              algorithm_filter=None if selected == ALL else selected)
        except OSError as e:
            messagebox.showerror("Không xuất được", f"Không ghi được file:\n{path}\n\n{e.strerror or e}")
            return
        messagebox.showinfo("Đã xuất", f"Đã xuất thống kê của {len(self._shown)} session ra:\n{path}")

    def _selected_session(self):
        """Session của dòng đang chọn trong bảng, hoặc None nếu chưa chọn dòng nào."""
        selection = self.listbox.curselection()
        if not selection or selection[0] >= len(self._shown):
            return None
        return self._shown[selection[0]]

    def delete_selected(self):
        session = self._selected_session()
        if session is None:
            messagebox.showinfo("Thông báo", "Hãy chọn một session để xóa.")
            return
        # Admin xem được session của người khác nhưng chỉ xóa được session của chính mình
        if session.username != self.manager.username:
            messagebox.showinfo("Thông báo", "Bạn chỉ có thể xóa session của chính mình.")
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa session {session.session_id}?"):
            return
        if self.manager.delete(session.session_id):
            try:
                self.manager.save()
            except session_manager.SessionDataError as e:
                messagebox.showerror("Không lưu được", f"{e}\n\nDữ liệu sẽ được tải lại từ file.")
                self.reload()  # đồng bộ lại với file
                return
        self.refresh()

    # ---------- nội bộ ----------
    def _on_select(self, _event):
        s = self._selected_session()
        if s:
            self._set_detail(f"Người dùng: {s.username}\n"
                             f"Ghi chú: {s.note}\n"
                             f"Dữ liệu gốc: {s.values}\nSau khi sắp xếp: {s.sorted_values}")

    def _set_detail(self, text):
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.config(state="disabled")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--demo"]
    username = args[0] if args else "Nhu"
    manager = session_manager.SessionManager(username)

    root = tk.Tk()
    # --demo: dùng dữ liệu sắp xếp giả để thử nút "Thêm session" khi chưa ghép với code sắp xếp thật
    provider = demo_result_provider if "--demo" in sys.argv else None
    panel = SessionPanel(root, manager, result_provider=provider)
    panel.pack(fill="both", expand=True)
    panel.reload()  # load dữ liệu; lỗi file được báo bằng hộp thoại thay vì làm chương trình sập
    root.mainloop()