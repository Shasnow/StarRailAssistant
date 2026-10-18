"""统一管理扩展自有资源及可写数据目录。"""
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = PACKAGE_ROOT / "resources"
CALIBRATION_ROOT = PACKAGE_ROOT / "calibration"
STRATEGY_ROOT = PACKAGE_ROOT / "strategies"
DEFAULT_STRATEGY = "himeko_level5_quality_level7_two_star_20261018"


def default_data_dir() -> Path:
    """存档与诊断沿用宿主的数据根目录，并与原版货币战争隔离。"""
    from SRACore.util.const import AppDataDir

    return Path(AppDataDir) / "currency_wars_plus"


# ssyb：裸名称从本包读取，显式路径保持用户指定含义。
def resolve_strategy_path(value) -> Path:
    """攻略名从扩展目录读取；带目录的路径按用户显式指定的位置读取。"""
    raw = Path(str(value).strip() or DEFAULT_STRATEGY)
    if raw.is_absolute() or raw.parent != Path("."):
        return raw.resolve()
    filename = raw.name if raw.suffix.lower() == ".json" else raw.name + ".json"
    return (STRATEGY_ROOT / filename).resolve()
