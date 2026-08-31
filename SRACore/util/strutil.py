def normalize_ocr_text(text: str) -> str:
    """
    Normalize a string by converting it to lowercase and stripping whitespace.

    Args:
        text (str): The input string to normalize.
    """
    return text.strip().replace("·", "").replace("•", "").replace("?", "").replace(" ", "")

def is_substring(a: str, b: str) -> bool:
    """
    Check if string A is a substring of string B or vice versa.

    Args:
        a (str): The potential substring.
        b (str): The string to check against.
    """
    return a in b or b in a