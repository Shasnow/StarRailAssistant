import sys

# type hints for StarRailAssistant

# if sys.version_info >= (3,12,6):
#     from typing import Callable , Any
#     type Point = tuple[float, float]
#     type Config = dict
#     type MetaData = dict
#     type TaskCall = Callable[..., None]
# else:
from typing import Tuple , Dict, Callable, Any
Point = Tuple[float, float]
Config = Dict
TaskCall = Callable[..., None]
MetaData = Dict
TaskArgv = Dict[str, Any]