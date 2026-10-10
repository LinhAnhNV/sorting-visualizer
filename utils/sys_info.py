"""C6 - Tiện ích dùng module sys."""

import platform
import sys


def get_system_info():
    """Chuỗi thông tin môi trường, để hiện ở menu Trợ giúp -> Giới thiệu."""
    v = sys.version_info
    return (
        f"Python {v.major}.{v.minor}.{v.micro}\n"
        f"Hệ điều hành: {platform.system()} {platform.release()}\n"
        f"Nền tảng: {sys.platform}"
    )


def exit_program(code=0):
    """Thoát chương trình với mã thoát `code` (0 = bình thường)."""
    sys.exit(code)