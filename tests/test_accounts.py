"""C7 - Kiểm thử phần C. Chạy từ thư mục gốc dự án: python -m unittest discover -s tests -v"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from accounts import api_client
from accounts.api_client import ApiError, fetch_numbers
from accounts.auth import (
    ACTION_MANAGE_ALL_SESSIONS, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME,
    AccountManager, AuthError, DataFileError, ValidationError,
)
from accounts.validators import (
    is_valid_email, is_valid_password, is_valid_phone, is_valid_username, parse_number_list,
)
from utils.json_storage import JsonStorage
from utils.sys_info import exit_program, get_system_info


class ValidatorTests(unittest.TestCase):
    def test_username(self):
        for ok in ["linh_anh01", "abcd", "A" * 20]:                     # đúng + biên 4 và 20
            self.assertTrue(is_valid_username(ok), ok)
        for bad in ["ab", "abc", "a" * 21, "ten co dau cach", "ten@123", ""]:
            self.assertFalse(is_valid_username(bad), bad)

    def test_email(self):
        for ok in ["khoa@gmail.com", "a.b+c@mail.huit.edu.vn", "user_1@site.io"]:
            self.assertTrue(is_valid_email(ok), ok)
        for bad in ["khoa@", "@gmail.com", "khoa.gmail.com", "khoa@gmail", ""]:
            self.assertFalse(is_valid_email(bad), bad)

    def test_password_boundary_7_and_8(self):
        self.assertFalse(is_valid_password("abc1234"))      # 7 ký tự
        self.assertTrue(is_valid_password("abc12345"))      # 8 ký tự
        for ok in ["matkhau123", "Passw0rdOK"]:
            self.assertTrue(is_valid_password(ok), ok)
        for bad in ["12345678", "abcdefgh", "abc12", ""]:
            self.assertFalse(is_valid_password(bad), bad)

    def test_phone(self):
        for ok in ["0912345678", "0123456789", "0999999999"]:
            self.assertTrue(is_valid_phone(ok), ok)
        for bad in ["091234567", "09a2345678", "1912345678", "09123456789", ""]:
            self.assertFalse(is_valid_phone(bad), bad)

    def test_parse_number_list_valid(self):
        self.assertEqual(parse_number_list("5, 3, 8, 1"), [5, 3, 8, 1])
        self.assertEqual(parse_number_list("42"), [42])
        self.assertEqual(parse_number_list(" -2 ,0,7 "), [-2, 0, 7])

    def test_parse_number_list_invalid(self):
        for bad in ["", "   ", "5,,3", "5, a, 3", "1.5, 2", "5, 3,"]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                parse_number_list(bad)
        with self.assertRaises(TypeError):
            parse_number_list(123)


class AccountTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.file = self.dir / "accounts.json"
        self.m = self._manager()

    def tearDown(self):
        self._tmp.cleanup()

    def _manager(self):
        return AccountManager(JsonStorage(self.file), self.dir / "login_log.txt")

    # --- C2: quyền
    def test_admin_can_manage_all_sessions_but_user_cannot(self):
        admin = self.m.login(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
        self.assertTrue(admin.can(ACTION_MANAGE_ALL_SESSIONS))
        self.m.logout()
        user = self.m.register("linh_anh01", "matkhau123", "la@gmail.com")
        self.assertFalse(user.can(ACTION_MANAGE_ALL_SESSIONS))
        self.assertTrue(user.can("run_sort"))

    # --- C3: đăng ký / đăng nhập
    def test_missing_file_creates_sample_admin(self):
        self.assertTrue(self.file.exists())
        self.assertEqual(self.m.login(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD).role, "admin")

    def test_empty_file_creates_sample_admin(self):
        self.file.write_text("  ", encoding="utf-8")
        m = self._manager()
        self.assertEqual(m.login(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD).role, "admin")

    def test_corrupt_file_raises_and_is_kept(self):
        self.file.write_text("{hong", encoding="utf-8")
        with self.assertRaises(DataFileError):
            self._manager()
        self.assertEqual(self.file.read_text(encoding="utf-8"), "{hong")

    def test_register_then_login_and_persist_after_restart(self):
        self.m.register("linh_anh01", "matkhau123", "la@gmail.com")
        self.assertEqual(self.m.login("linh_anh01", "matkhau123").username, "linh_anh01")
        again = self._manager()                     # "tắt mở lại"
        self.assertEqual(again.login("LINH_ANH01", "matkhau123").role, "user")

    def test_new_account_is_always_user_role(self):
        self.assertEqual(self.m.register("khoa_b", "matkhau123", "k@gmail.com").role, "user")

    def test_register_duplicate_username_rejected(self):
        self.m.register("khoa_b", "matkhau123", "k@gmail.com")
        with self.assertRaises(ValidationError):
            self.m.register("KHOA_B", "matkhau456", "khac@gmail.com")

    def test_register_invalid_data_lists_all_reasons(self):
        with self.assertRaises(ValidationError) as ctx:
            self.m.register("ab", "123", "khoa@")
        self.assertGreaterEqual(len(ctx.exception.errors), 4)

    def test_login_wrong_gives_same_generic_message(self):
        with self.assertRaises(AuthError) as wrong_pw:
            self.m.login(DEFAULT_ADMIN_USERNAME, "saimatkhau1")
        with self.assertRaises(AuthError) as wrong_user:
            self.m.login("khongco", "matkhau123")
        self.assertEqual(str(wrong_pw.exception), "Sai tên đăng nhập hoặc mật khẩu")
        self.assertEqual(str(wrong_pw.exception), str(wrong_user.exception))
        self.assertFalse(self.m.is_logged_in)

    def test_password_not_stored_in_plaintext(self):
        self.m.register("khoa_b", "matkhau123", "k@gmail.com")
        self.assertNotIn("matkhau123", self.file.read_text(encoding="utf-8"))

    def test_change_password(self):
        self.m.register("khoa_b", "matkhau123", "k@gmail.com")
        with self.assertRaises(AuthError):                         # chưa đăng nhập
            self.m.change_password("matkhau123", "moi12345")
        self.m.login("khoa_b", "matkhau123")
        with self.assertRaises(AuthError):                         # sai mật khẩu cũ
            self.m.change_password("saimatkhau1", "moi12345")
        with self.assertRaises(ValidationError):                   # mật khẩu mới yếu (7 ký tự)
            self.m.change_password("matkhau123", "moi1234")
        self.m.change_password("matkhau123", "moi12345")
        self.m.logout()
        self.assertEqual(self._manager().login("khoa_b", "moi12345").username, "khoa_b")

    def test_login_log_written(self):
        self.m.login(DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)
        with self.assertRaises(AuthError):
            self.m.login(DEFAULT_ADMIN_USERNAME, "sai")
        log = (self.dir / "login_log.txt").read_text(encoding="utf-8")
        self.assertIn("THANH CONG", log)
        self.assertIn("THAT BAI", log)


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("không phải JSON")
        return self._payload


class ApiClientTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(api_client, "API_DATA_FILE", Path(self._tmp.name) / "api_data.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def _fetch(self, response=None, side_effect=None, **kwargs):
        with mock.patch("accounts.api_client.requests.get", return_value=response, side_effect=side_effect):
            return fetch_numbers(kwargs.pop("count", 5), 1, 100, **kwargs)

    def test_success_returns_numbers_and_saves_json(self):
        result = self._fetch(FakeResponse(payload=[5, 3, 8, 1, 9]))
        self.assertEqual(result.numbers, [5, 3, 8, 1, 9])
        self.assertEqual(result.removed, 0)
        saved = json.loads(api_client.API_DATA_FILE.read_text(encoding="utf-8"))
        self.assertEqual(saved["numbers"], [5, 3, 8, 1, 9])
        self.assertEqual(saved["source"], api_client.SOURCE_NAME)
        self.assertIn("fetched_at", saved)

    def test_cleaning_removes_bad_items_and_reports_count(self):
        result = self._fetch(FakeResponse(payload=[5, "7", None, "", "abc", 3.5, 4.0, 500, True]), count=9)
        self.assertEqual(result.numbers, [5, 7, 4])
        self.assertEqual(result.removed, 6)

    def test_plain_text_response(self):
        result = self._fetch(FakeResponse(text="4\n8\n15\n"), count=3)
        self.assertEqual(result.numbers, [4, 8, 15])

    def test_no_network_raises_clear_error(self):
        with self.assertRaises(ApiError) as ctx:
            self._fetch(side_effect=requests.exceptions.ConnectionError())
        self.assertIn("kết nối", str(ctx.exception))

    def test_timeout_raises_clear_error(self):
        with self.assertRaises(ApiError) as ctx:
            self._fetch(side_effect=requests.exceptions.Timeout())
        self.assertIn("thời gian chờ", str(ctx.exception))

    def test_http_error_codes(self):
        for status in (404, 429, 500):
            with self.assertRaises(ApiError, msg=status):
                self._fetch(FakeResponse(status=status))

    def test_malformed_data_raises_error(self):
        for payload in ({"a": 1}, [], ["x", None]):
            with self.assertRaises(ApiError, msg=payload):
                self._fetch(FakeResponse(payload=payload))

    def test_bad_arguments_raise_value_error(self):
        for args in [(0, 1, 10), (5, 10, 1), (5000, 1, 10), ("5", 1, 10)]:
            with self.assertRaises(ValueError, msg=args):
                fetch_numbers(*args)

    def test_unsavable_file_still_returns_numbers(self):
        with mock.patch.object(api_client, "API_DATA_FILE", Path(self._tmp.name) / "x" / "api.json"), \
             mock.patch("accounts.api_client.Path.mkdir", side_effect=PermissionError):
            result = self._fetch(FakeResponse(payload=[1, 2, 3]), count=3)
        self.assertEqual(result.numbers, [1, 2, 3])
        self.assertFalse(result.saved)


class SysInfoTests(unittest.TestCase):
    def test_info_contains_python_and_os(self):
        info = get_system_info()
        self.assertIn("Python", info)
        self.assertIn("Hệ điều hành", info)

    def test_exit_program_uses_exit_code(self):
        with self.assertRaises(SystemExit) as ctx:
            exit_program(3)
        self.assertEqual(ctx.exception.code, 3)


if __name__ == "__main__":
    unittest.main()