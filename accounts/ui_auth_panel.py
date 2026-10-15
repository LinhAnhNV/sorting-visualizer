"""C5 - Giao diện đăng nhập / đăng ký / đổi mật khẩu bằng Tkinter.

Quy ước layout: trong mỗi vùng chứa (Frame/Toplevel) chỉ dùng grid(), không trộn với pack().
Chạy thử riêng:  python -m accounts.ui_auth_panel   (từ thư mục gốc dự án)
"""

import tkinter as tk
from tkinter import messagebox

from accounts.auth import AccountError, AccountManager, ValidationError

FONT = ("Helvetica", 11)
FONT_TITLE = ("Helvetica", 16, "bold")
PAD = 6


def _show_error(parent, exc):
    """Hiện hộp thoại lỗi; ValidationError thì liệt kê từng lý do."""
    if isinstance(exc, ValidationError):
        messagebox.showerror("Dữ liệu chưa hợp lệ",
                             "\n".join(f"• {e}" for e in exc.errors), parent=parent)
    else:
        messagebox.showerror("Lỗi", str(exc), parent=parent)


class AuthPanel(tk.Frame):
    """Khung có 2 chế độ: Đăng nhập / Đăng ký. Đăng nhập đúng thì gọi on_login_success(user)."""

    def __init__(self, parent, manager, on_login_success):
        super().__init__(parent, padx=24, pady=24)
        self._manager = manager
        self._on_login_success = on_login_success
        self._mode = "login"

        self._username = tk.StringVar()
        self._email = tk.StringVar()
        self._password = tk.StringVar()
        self._confirm = tk.StringVar()
        self._show_pw = tk.BooleanVar(value=False)

        self._build()
        self._apply_mode()

    # ---------- dựng giao diện (chỉ dùng grid trong self) ----------
    def _build(self):
        self.columnconfigure(1, weight=1)    # ô nhập co giãn theo cửa sổ

        self._title = tk.Label(self, font=FONT_TITLE)
        self._title.grid(row=0, column=0, columnspan=2, pady=(0, 12))

        self._row_widgets = {}
        rows = [
            ("username", "Tên đăng nhập:", self._username, False),
            ("email", "Email:", self._email, False),
            ("password", "Mật khẩu:", self._password, True),
            ("confirm", "Nhập lại mật khẩu:", self._confirm, True),
        ]
        for i, (key, text, var, secret) in enumerate(rows, start=1):
            label = tk.Label(self, text=text, font=FONT, anchor="w")
            entry = tk.Entry(self, textvariable=var, font=FONT, show="*" if secret else "")
            label.grid(row=i, column=0, sticky="w", padx=PAD, pady=PAD)
            entry.grid(row=i, column=1, sticky="ew", padx=PAD, pady=PAD)
            entry.bind("<Return>", lambda _e: self._on_submit())   # Enter = bấm nút
            self._row_widgets[key] = (label, entry)

        self._pw_entries = [self._row_widgets["password"][1], self._row_widgets["confirm"][1]]
        tk.Checkbutton(self, text="Hiện mật khẩu", font=FONT, variable=self._show_pw,
                       command=self._toggle_password).grid(row=5, column=1, sticky="w", padx=PAD)

        self._submit_btn = tk.Button(self, font=FONT, command=self._on_submit)
        self._submit_btn.grid(row=6, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(12, PAD))
        self._switch_btn = tk.Button(self, font=FONT, relief="flat", command=self._switch_mode)
        self._switch_btn.grid(row=7, column=0, columnspan=2, sticky="ew", padx=PAD)

    def _apply_mode(self):
        register = self._mode == "register"
        for key in ("email", "confirm"):                    # chỉ hiện khi đăng ký
            for widget in self._row_widgets[key]:
                widget.grid() if register else widget.grid_remove()
        self._title.config(text="Đăng ký tài khoản" if register else "Đăng nhập")
        self._submit_btn.config(text="Đăng ký" if register else "Đăng nhập")
        self._switch_btn.config(text="Đã có tài khoản? Đăng nhập" if register
                                else "Chưa có tài khoản? Đăng ký")

    def _toggle_password(self):
        char = "" if self._show_pw.get() else "*"
        for entry in self._pw_entries:
            entry.config(show=char)

    def _switch_mode(self):
        self._mode = "register" if self._mode == "login" else "login"
        self._password.set("")
        self._confirm.set("")
        self._apply_mode()

    # ---------- xử lý sự kiện ----------
    def _on_submit(self):
        username = self._username.get().strip()
        password = self._password.get()
        try:
            if self._mode == "login":
                user = self._manager.login(username, password)
                self._password.set("")
                self._on_login_success(user)
            else:
                if password != self._confirm.get():
                    raise ValidationError(["Mật khẩu nhập lại chưa khớp, hãy gõ lại cho giống nhau"])
                self._manager.register(username, password, self._email.get().strip())
                messagebox.showinfo("Thành công", "Tạo tài khoản thành công. Hãy đăng nhập.", parent=self)
                self._mode = "login"
                self._password.set("")
                self._confirm.set("")
                self._apply_mode()
        except AccountError as e:
            _show_error(self, e)

    def reset(self):
        """A gọi sau khi đăng xuất: xóa ô nhập và về màn hình đăng nhập."""
        for var in (self._username, self._email, self._password, self._confirm):
            var.set("")
        self._mode = "login"
        self._apply_mode()


class ChangePasswordDialog(tk.Toplevel):
    """Hộp thoại đổi mật khẩu (menu của main.py sẽ mở). Cần manager đang có người đăng nhập."""

    def __init__(self, parent, manager):
        super().__init__(parent)
        self.title("Đổi mật khẩu")
        self.resizable(False, False)
        self._manager = manager
        self._old = tk.StringVar()
        self._new = tk.StringVar()
        self._confirm = tk.StringVar()

        body = tk.Frame(self, padx=20, pady=16)
        body.grid(row=0, column=0)
        body.columnconfigure(1, weight=1)
        first = None
        for i, (text, var) in enumerate([("Mật khẩu cũ:", self._old),
                                         ("Mật khẩu mới:", self._new),
                                         ("Nhập lại mật khẩu mới:", self._confirm)]):
            tk.Label(body, text=text, font=FONT, anchor="w").grid(row=i, column=0, sticky="w", padx=PAD, pady=PAD)
            entry = tk.Entry(body, textvariable=var, font=FONT, show="*")
            entry.grid(row=i, column=1, sticky="ew", padx=PAD, pady=PAD)
            entry.bind("<Return>", lambda _e: self._on_submit())
            first = first or entry

        buttons = tk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=2, pady=(12, 0))
        tk.Button(buttons, text="Đổi mật khẩu", font=FONT, command=self._on_submit).grid(row=0, column=0, padx=PAD)
        tk.Button(buttons, text="Hủy", font=FONT, command=self.destroy).grid(row=0, column=1, padx=PAD)

        self.transient(parent)
        self.grab_set()
        first.focus_set()

    def _on_submit(self):
        try:
            if self._new.get() != self._confirm.get():
                raise ValidationError(["Mật khẩu mới nhập lại chưa khớp"])
            self._manager.change_password(self._old.get(), self._new.get())
        except AccountError as e:
            _show_error(self, e)
            return
        messagebox.showinfo("Thành công", "Đã đổi mật khẩu.", parent=self)
        self.destroy()


def open_change_password_dialog(parent, manager):
    """Hàm tiện cho menu: mở hộp thoại đổi mật khẩu (nhắc đăng nhập nếu chưa)."""
    if not manager.is_logged_in:
        messagebox.showwarning("Chưa đăng nhập", "Hãy đăng nhập trước khi đổi mật khẩu.", parent=parent)
        return
    ChangePasswordDialog(parent, manager)


if __name__ == "__main__":
    # Cửa sổ thử riêng cho phần C: đăng ký, đăng nhập, đổi mật khẩu
    root = tk.Tk()
    root.title("Thử AuthPanel")
    manager = AccountManager()

    welcome = tk.Frame(root, padx=24, pady=24)
    welcome_label = tk.Label(welcome, font=FONT_TITLE)
    welcome_label.grid(row=0, column=0, pady=(0, 12))

    def on_login_success(user):
        welcome_label.config(text=f"Xin chào {user.username} ({user.role})")
        panel.pack_forget()
        welcome.pack(fill="both", expand=True)

    def do_logout():
        manager.logout()
        welcome.pack_forget()
        panel.reset()
        panel.pack(fill="both", expand=True)

    tk.Button(welcome, text="Đổi mật khẩu", font=FONT,
              command=lambda: open_change_password_dialog(root, manager)).grid(row=1, column=0, sticky="ew", pady=PAD)
    tk.Button(welcome, text="Đăng xuất", font=FONT, command=do_logout).grid(row=2, column=0, sticky="ew")

    panel = AuthPanel(root, manager, on_login_success)
    panel.pack(fill="both", expand=True)
    root.mainloop()