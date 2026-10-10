"""C2 + C3 - Lớp User (phân quyền) và AccountManager (đăng ký, đăng nhập, đổi mật khẩu)."""

import hashlib
import hmac
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from accounts.validators import email_errors, password_errors, username_errors

# Đường dẫn tính từ vị trí file => không phụ thuộc máy.
# (Nếu A đã có DATA_DIR trong config.py thì có thể import từ đó thay cho 3 dòng này.)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
LOGIN_LOG_FILE = DATA_DIR / "login_log.txt"

ROLE_ADMIN = "admin"
ROLE_USER = "user"

# Các action trong ứng dụng. B/A có thể thêm action mới vào USER_ACTIONS nếu người dùng thường được dùng.
ACTION_MANAGE_ALL_SESSIONS = "manage_all_sessions"   # xem/sửa/xóa phiên của người khác (chỉ admin)
USER_ACTIONS = frozenset({"run_sort", "manage_own_sessions", "view_stats", "fetch_api_data"})

PBKDF2_ITERATIONS = 200_000

# Dữ liệu mẫu: tài khoản admin tự tạo khi chưa có file. Nhớ đổi mật khẩu sau khi đăng nhập lần đầu.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin12345"


# ---------------------------------------------------------------- Lỗi riêng
class AccountError(Exception):
    """Lớp cha của các lỗi tài khoản (giao diện chỉ cần bắt lớp này)."""


class ValidationError(AccountError):
    """Dữ liệu nhập sai. `errors` là danh sách lý do + cách sửa."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class AuthError(AccountError):
    """Sai thông tin đăng nhập, sai mật khẩu cũ hoặc chưa đăng nhập."""


class DataFileError(AccountError):
    """File accounts.json không đọc/ghi được."""


# ---------------------------------------------------------------- Băm mật khẩu
def _hash_password(password, salt=None):
    """Trả về (salt_hex, hash_hex). Không bao giờ lưu mật khẩu gốc."""
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password, salt_hex, hash_hex):
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:      # salt trong file bị hỏng
        return False
    _, digest_hex = _hash_password(password, salt)
    return hmac.compare_digest(digest_hex, hash_hex)


# ---------------------------------------------------------------- C2: User + quyền
class User(ABC):
    """Lớp cha trừu tượng; mỗi vai trò ghi đè can() (đa hình)."""

    ROLE = ""

    def __init__(self, username, email, salt, password_hash, created_at=None):
        self._username = username
        self._email = email
        self._salt = salt
        self._password_hash = password_hash
        self._created_at = created_at or datetime.now().isoformat(timespec="seconds")

    @property
    def username(self):
        return self._username

    @property
    def email(self):
        return self._email

    @property
    def role(self):
        return self.ROLE

    def check_password(self, plain_password):
        return _verify_password(plain_password, self._salt, self._password_hash)

    @abstractmethod
    def can(self, action):
        """True/False: vai trò này có được làm `action` không."""

    def with_password(self, salt, password_hash):
        return type(self)(self._username, self._email, salt, password_hash, self._created_at)

    def to_dict(self):
        return {
            "username": self._username,
            "email": self._email,
            "role": self.ROLE,
            "salt": self._salt,
            "password_hash": self._password_hash,
            "created_at": self._created_at,
        }


class AdminUser(User):
    ROLE = ROLE_ADMIN

    def can(self, action):
        return True     # Quản trị viên được mọi action


class NormalUser(User):
    ROLE = ROLE_USER

    def can(self, action):
        return action in USER_ACTIONS


_ROLE_CLASSES = {ROLE_ADMIN: AdminUser, ROLE_USER: NormalUser}


def _user_from_dict(data):
    """Raise KeyError/ValueError/TypeError nếu bản ghi hỏng."""
    cls = _ROLE_CLASSES.get(data["role"])
    if cls is None:
        raise ValueError(f"vai trò không hợp lệ: {data['role']!r}")
    return cls(data["username"], data["email"], data["salt"],
               data["password_hash"], data.get("created_at"))


# ---------------------------------------------------------------- C3: AccountManager
class AccountManager:
    """Quản lý tài khoản. `storage` là JsonStorage của B (cần .load() và .save(data))."""

    def __init__(self, storage=None, log_file=LOGIN_LOG_FILE):
        if storage is None:
            from utils.json_storage import JsonStorage   # file của Khoa (B)
            storage = JsonStorage(ACCOUNTS_FILE)
        self._storage = storage
        self._log_file = Path(log_file)
        self._users = {}        # key = username viết thường
        self._current = None
        self._load()

    # --- trạng thái đăng nhập
    @property
    def current_user(self):
        return self._current

    @property
    def is_logged_in(self):
        return self._current is not None

    # --- chức năng
    def register(self, username, password, email):
        """Tạo tài khoản mới. Luôn là role 'user' (không cho tự chọn admin)."""
        errors = username_errors(username) + password_errors(password) + email_errors(email)
        if errors:
            raise ValidationError(errors)
        if username.lower() in self._users:
            raise ValidationError([f"Username '{username}' đã tồn tại, hãy chọn tên khác"])

        salt, pw_hash = _hash_password(password)
        user = NormalUser(username, email, salt, pw_hash)
        snapshot = dict(self._users)
        self._users[username.lower()] = user
        self._save(snapshot)
        return user

    def login(self, username, password):
        """Trả về User nếu đúng; báo lỗi chung (không nói rõ cái nào sai) nếu sai."""
        user = self._users.get(username.lower()) if isinstance(username, str) else None
        ok = user is not None and isinstance(password, str) and user.check_password(password)
        self._log_login(username, ok)
        if not ok:
            raise AuthError("Sai tên đăng nhập hoặc mật khẩu")
        self._current = user
        return user

    def logout(self):
        self._current = None

    def change_password(self, old_password, new_password):
        """Phải đang đăng nhập, đúng mật khẩu cũ, mật khẩu mới qua kiểm tra Regex."""
        if self._current is None:
            raise AuthError("Bạn cần đăng nhập trước khi đổi mật khẩu")
        if not self._current.check_password(old_password):
            raise AuthError("Mật khẩu cũ không đúng")
        errors = password_errors(new_password)
        if new_password == old_password:
            errors.append("Mật khẩu mới phải khác mật khẩu cũ")
        if errors:
            raise ValidationError(errors)

        salt, pw_hash = _hash_password(new_password)
        updated = self._current.with_password(salt, pw_hash)
        snapshot = dict(self._users)
        self._users[updated.username.lower()] = updated
        self._save(snapshot)
        self._current = updated

    # --- nội bộ
    def _load(self):
        try:
            raw = self._storage.load()
        except (OSError, ValueError) as e:   # file hỏng / không có quyền (JSONDecodeError là ValueError)
            raise DataFileError(
                f"Không đọc được file tài khoản ({e}). File được giữ nguyên, không bị ghi đè."
            ) from None
        if not raw:     # chưa có file hoặc file rỗng -> tạo dữ liệu mẫu
            self._seed_default_admin()
            return
        if not isinstance(raw, list):
            raise DataFileError("File tài khoản sai định dạng (cần là một danh sách).")
        users = {}
        for item in raw:
            try:
                user = _user_from_dict(item)
            except (KeyError, TypeError, ValueError) as e:
                raise DataFileError(f"Có bản ghi tài khoản bị hỏng ({e}).") from None
            users[user.username.lower()] = user
        self._users = users

    def _seed_default_admin(self):
        salt, pw_hash = _hash_password(DEFAULT_ADMIN_PASSWORD)
        admin = AdminUser(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, salt, pw_hash)
        snapshot = {}
        self._users = {admin.username.lower(): admin}
        self._save(snapshot)

    def _save(self, snapshot):
        """Ghi file; nếu lỗi thì trả bộ nhớ về trạng thái cũ để không bị lệch với file."""
        try:
            self._storage.save([u.to_dict() for u in self._users.values()])
        except (OSError, ValueError, TypeError) as e:
            self._users = snapshot
            raise DataFileError(f"Không ghi được file tài khoản: {e}") from None

    def _log_login(self, username, success):
        """Nhật ký đăng nhập: thời gian | tên tài khoản | thành công/thất bại."""
        line = (f"{datetime.now().isoformat(timespec='seconds')} | {username} | "
                f"{'THANH CONG' if success else 'THAT BAI'}\n")
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass    # không ghi được nhật ký thì bỏ qua, không làm ứng dụng dừng