import abc


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


class StrMatcher(abc.ABC):
    def __init__(self, value: str):
        self.value = value

    @abc.abstractmethod
    def match(self, other: str) -> bool:
        """Check if the other string matches the criteria defined by this matcher."""
        pass


class ContainsMatcher(StrMatcher):
    def match(self, other: str) -> bool:
        return self.value in other


class EqualsMatcher(StrMatcher):
    def match(self, other: str) -> bool:
        return self.value == other