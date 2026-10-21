"""Panel quản lý lịch sử session.

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
from tkinter import ttk, messagebox

import session_manager
import stats
import ui_compare_canvas

ALGORITHMS = ["Bubble Sort", "Selection Sort", "Insertion Sort"]
ALL = "Tất cả"  # lựa chọn "không lọc"


# Các khóa bắt buộc trong kết quả sắp xếp mà phần code sắp xếp phải cung cấp
RESULT_KEYS = ("values", "sorted_values", "swaps", "comparisons")


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

        form = ttk.Frame(self, padding=12)
        form.pack()

        # Tóm tắt dữ liệu sắp được lưu (chỉ đọc) để người dùng biết mình đang lưu kết quả nào
        summary = (f"Kết quả sắp xếp sẽ được lưu: {len(result['values'])} phần tử, "
                   f"{result['swaps']} swaps, {result['comparisons']} so sánh")
        ttk.Label(form, text=summary, foreground="gray").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(form, text="Thuật toán").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Combobox(form, textvariable=self.algorithm, values=ALGORITHMS,
                     state="readonly", width=34).grid(row=1, column=1, pady=4)
        ttk.Label(form, text="Ghi chú").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(form, textvariable=self.note, width=36).grid(row=2, column=1, pady=4)

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Lưu", command=self.submit).pack(side="left", padx=4)
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(side="left", padx=4)

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


class SessionPanel(ttk.Frame):
    COLUMNS = (
        ("id", "ID", 80),
        ("user", "User", 90),
        ("algorithm", "Thuật toán", 130),
        ("size", "Số phần tử", 90),
        ("swaps", "Swaps", 70),
        ("comparisons", "So sánh", 80),
        ("time", "Thời gian", 150),
        ("note", "Ghi chú", 200),
    )

    def __init__(self, master, manager, result_provider=None):
        super().__init__(master, padding=8)
        self.manager = manager
        self.result_provider = result_provider  # hàm lấy kết quả sắp xếp từ code của người khác
        self._row_sessions = {}   # iid của dòng trong bảng -> Session
        self._compare_window = None
        self._build()
        self.refresh()

    def _build(self):
        # Thanh chọn user: người khác nhập tên của mình rồi bấm "Đổi user"
        user_bar = ttk.Frame(self)
        user_bar.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(user_bar, text="User:").pack(side="left")
        self.user_var = tk.StringVar(value=self.manager.username)
        user_entry = ttk.Entry(user_bar, textvariable=self.user_var, width=20)
        user_entry.pack(side="left", padx=6)
        user_entry.bind("<Return>", lambda _e: self.switch_user())
        ttk.Button(user_bar, text="Đổi user", command=self.switch_user).pack(side="left")
        self.role_label = ttk.Label(user_bar, foreground="gray")
        self.role_label.pack(side="left", padx=12)

        # Thanh lọc / phạm vi xem
        tools_bar = ttk.Frame(self)
        tools_bar.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(tools_bar, text="Lọc thuật toán:").pack(side="left")
        self.filter_var = tk.StringVar(value=ALL)
        self.filter_box = ttk.Combobox(tools_bar, textvariable=self.filter_var,
                                       values=[ALL] + ALGORITHMS, state="readonly", width=16)
        self.filter_box.pack(side="left", padx=6)
        self.filter_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        # Chỉ admin mới bật được ô này
        self.view_all = tk.BooleanVar(value=False)
        self.view_all_check = ttk.Checkbutton(tools_bar, text="Xem tất cả user (admin)",
                                              variable=self.view_all, command=self.refresh)
        self.view_all_check.pack(side="left", padx=(20, 0))

        # Bảng danh sách session
        self.tree = ttk.Treeview(self, columns=[c[0] for c in self.COLUMNS],
                                 show="headings", selectmode="browse", height=10)
        for key, title, width in self.COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        scroll.grid(row=2, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Chi tiết session đang chọn
        self.detail = tk.Text(self, height=4, state="disabled", wrap="word")
        self.detail.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Nút chức năng
        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(buttons, text="So sánh thuật toán", command=self.open_compare).pack(side="left", padx=4)
        ttk.Button(buttons, text="Thêm session", command=self.add_session).pack(side="left", padx=4)
        ttk.Button(buttons, text="Làm mới", command=self.reload).pack(side="left", padx=4)
        ttk.Button(buttons, text="Xóa session", command=self.delete_selected).pack(side="left", padx=4)

        # Thống kê
        self.stats_label = ttk.Label(self, justify="left")
        self.stats_label.grid(row=5, column=0, columnspan=2, sticky="w")

        # Cho biết đang đọc file nào, có bao nhiêu session
        self.status_label = ttk.Label(self, foreground="gray")
        self.status_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

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

    def _update_filter_options(self, base):
        """Danh sách lọc = các thuật toán có sẵn + thuật toán lạ xuất hiện trong dữ liệu."""
        extra = sorted({s.algorithm for s in base} - set(ALGORITHMS))
        options = [ALL] + ALGORITHMS + extra
        self.filter_box.config(values=options)
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

        self.tree.delete(*self.tree.get_children())
        self._row_sessions = {}
        for s in shown:
            iid = self.tree.insert("", "end", values=(
                s.session_id, s.username, s.algorithm, len(s.values), s.swaps,
                s.comparisons, s.create_at.replace("T", " "), s.note,
            ))
            self._row_sessions[iid] = s
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

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Thông báo", "Hãy chọn một session để xóa.")
            return
        session = self._row_sessions.get(selected[0])
        if session is None:
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
        selected = self.tree.selection()
        if not selected:
            return
        s = self._row_sessions.get(selected[0])
        if s:
            self._set_detail(f"Người dùng: {s.username}\n"
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