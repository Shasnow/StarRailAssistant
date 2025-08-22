import base64

import win32crypt


def win_encryptor(note: str, description: str = None, entropy: bytes = None) -> str:
    """使用Windows DPAPI加密数据"""

    if note == "":
        return ""
    try:
        encrypted = win32crypt.CryptProtectData(
            note.encode("utf-8"), description, entropy, None, None, 0
        )
    except Exception:
        return ""
    return base64.b64encode(encrypted).decode("utf-8")


def win_decryptor(note: str, entropy: bytes = None) -> str:
    """使用Windows DPAPI解密数据"""

    if note == "":
        return ""
    try:
        decrypted = win32crypt.CryptUnprotectData(
            base64.b64decode(note), entropy, None, None, 0
        )
    except Exception:
        return ""
    return decrypted[1].decode("utf-8")
