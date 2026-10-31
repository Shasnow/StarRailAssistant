import base64
import sys


def encryptor(plaintext: str | None = None) -> str:
    """使用Windows DPAPI加密数据，返回与 decryptor 对称的 base64 字符串。

    非 Windows 平台退化为 base64 编码（与 decryptor 的非 Windows 分支对称），
    加密失败时返回空字符串。
    """

    if not plaintext:
        return ""
    try:
        plain_bytes = plaintext.encode("utf-8")
        if sys.platform == "win32":
            import win32crypt
            encrypted_bytes = win32crypt.CryptProtectData(  # type: ignore
                plain_bytes,
                None,
                None,
                None,
                None,
                0
            )[1]
        else:
            encrypted_bytes = plain_bytes
        return base64.b64encode(encrypted_bytes).decode("utf-8")
    except Exception:
        return ""


def decryptor(entropy: str | None = None) -> str:
    """使用Windows DPAPI解密数据"""

    if not entropy:
        return ""
    try:
        encrypted_bytes = base64.b64decode(entropy)
        # 参数说明：加密数据、熵（C# 中为 null）、标志（0 表示当前用户）
        if sys.platform == "win32":
            import win32crypt
            decrypted_bytes = win32crypt.CryptUnprotectData( # type: ignore
                encrypted_bytes,
                None,
                None,
                None,
                0
            )[1]  # 返回元组，第2个元素是解密后的字节
        else:
            decrypted_bytes = encrypted_bytes
        return decrypted_bytes.decode("utf-8")

    except Exception:
        return ""
