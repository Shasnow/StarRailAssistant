import base64
import sys


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
