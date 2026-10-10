"""C1 - Kiểm tra dữ liệu nhập bằng Regular Expression (module re).

Mọi hàm ở đây là hàm thuần: nhận dữ liệu, trả kết quả, không đụng đến giao diện hay file.
- *_errors(x)   -> list[str]: danh sách lý do sai (rỗng = hợp lệ), có gợi ý cách sửa.
- is_valid_*(x) -> bool.
"""

import re

USERNAME_MIN_LEN = 4
USERNAME_MAX_LEN = 20
PASSWORD_MIN_LEN = 8

# fullmatch => phải khớp TOÀN BỘ chuỗi (không bị lọt ký tự thừa/xuống dòng)
_USERNAME_CHARS_RE = re.compile(r"[A-Za-z0-9_]*")
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"
)
_PHONE_VN_RE = re.compile(r"0[0-9]{9}")


def username_errors(username):
    if not isinstance(username, str):
        return ["Username phải là chuỗi ký tự"]
    errors = []
    if not USERNAME_MIN_LEN <= len(username) <= USERNAME_MAX_LEN:
        errors.append(f"Username cần có {USERNAME_MIN_LEN}-{USERNAME_MAX_LEN} ký tự")
    if not _USERNAME_CHARS_RE.fullmatch(username):
        errors.append("Username chỉ được gồm chữ cái không dấu, chữ số và dấu gạch dưới '_'")
    return errors


def email_errors(email):
    if not isinstance(email, str):
        return ["Email phải là chuỗi ký tự"]
    if not _EMAIL_RE.fullmatch(email):
        return ["Email cần có dạng tên@tenmien.com (ví dụ: khoa@gmail.com)"]
    return []


def password_errors(password):
    if not isinstance(password, str):
        return ["Mật khẩu phải là chuỗi ký tự"]
    errors = []
    if len(password) < PASSWORD_MIN_LEN:
        errors.append(f"Mật khẩu cần tối thiểu {PASSWORD_MIN_LEN} ký tự")
    if not re.search(r"[A-Za-z]", password):
        errors.append("Mật khẩu cần có ít nhất 1 chữ cái")
    if not re.search(r"[0-9]", password):
        errors.append("Mật khẩu cần có ít nhất 1 chữ số")
    return errors


def phone_errors(phone):
    if not isinstance(phone, str):
        return ["Số điện thoại phải là chuỗi ký tự"]
    if not _PHONE_VN_RE.fullmatch(phone):
        return ["Số điện thoại cần đủ 10 chữ số và bắt đầu bằng 0 (ví dụ: 0912345678)"]
    return []


def is_valid_username(username):
    return not username_errors(username)


def is_valid_email(email):
    return not email_errors(email)


def is_valid_password(password):
    return not password_errors(password)


def is_valid_phone(phone):
    return not phone_errors(phone)


def parse_number_list(text):
    """Chuyển "5, 3, 8, 1" -> [5, 3, 8, 1] (A và B dùng để nhập dãy số).

    Raise TypeError nếu text không phải chuỗi.
    Raise ValueError (kèm thông báo rõ ràng) nếu rỗng, có phần tử rỗng hoặc không phải số nguyên.
    """
    if not isinstance(text, str):
        raise TypeError("Dữ liệu phải là chuỗi")
    if not text.strip():
        raise ValueError("Chưa nhập dãy số. Ví dụ: 5, 3, 8, 1")

    result = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            raise ValueError("Có phần tử trống (thừa dấu ','). Ví dụ đúng: 5, 3, 8, 1")
        try:
            result.append(int(part))
        except ValueError:
            raise ValueError(f"'{part}' không phải số nguyên") from None
    return result