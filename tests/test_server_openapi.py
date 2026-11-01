"""校验 ``GET /openapi/v1.json`` 暴露 WebUI 动态表单所需的组件与点号别名。"""

from __future__ import annotations

import pytest

pytest.importorskip("litestar")

from litestar.testing import TestClient  # noqa: E402

from SRAServer.app import create_app  # noqa: E402
from SRAServer.config import ServerConfig  # noqa: E402

_BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="module")
def schema() -> dict:
    config = ServerConfig.load(host="127.0.0.1", port=5073, webui=False)
    app = create_app(config)
    with TestClient(app, base_url=_BASE_URL) as client:
        response = client.get("/openapi/v1.json")
        assert response.status_code == 200
        return response.json()


def test_top_level_components_present(schema: dict) -> None:
    schemas = schema["components"]["schemas"]
    assert "TasksConfig" in schemas
    assert "AppSettings" in schemas


def test_nested_ref_targets(schema: dict) -> None:
    schemas = schema["components"]["schemas"]
    assert schemas["TasksConfig"]["properties"]["startGame"]["$ref"] == "#/components/schemas/StartGameConfig"
    assert schemas["AppSettings"]["properties"]["general"]["$ref"] == "#/components/schemas/GeneralSettings"
    for name in (
        "StartGameConfig",
        "TrailblazePowerConfig",
        "ReceiveRewardsConfig",
        "CosmicStrifeConfig",
        "MissionAccomplishedConfig",
        "GeneralSettings",
        "DisplaySettings",
        "UpdateSettings",
        "AdvancedSettings",
        "NotificationSettings",
    ):
        assert name in schemas, name


def test_tasks_config_property_order(schema: dict) -> None:
    properties = schema["components"]["schemas"]["TasksConfig"]["properties"]
    assert list(properties) == [
        "name",
        "startGame",
        "trailblazePower",
        "receiveRewards",
        "cosmicStrife",
        "missionAccomplished",
        "version",
    ]


def test_dotted_aliases_kept(schema: dict) -> None:
    general = schema["components"]["schemas"]["GeneralSettings"]["properties"]
    assert "gameArgs.fullScreenMode" in general
    assert "gamePath.uris" in general

    start_game = schema["components"]["schemas"]["StartGameConfig"]["properties"]
    assert "game.path" in start_game
    assert "game.channel" in start_game