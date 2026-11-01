"""SRAServer HTTP 接口的隔离测试。

用临时目录承载 cache.json / configs / settings.json 与日志，完全不触碰真实 AppDataDir。
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any, Iterator

import pytest

pytest.importorskip("litestar")

from litestar.testing import TestClient  # noqa: E402

from SRACore.util import data_persister  # noqa: E402
from SRACore.util import logger as sra_logger  # noqa: E402
from SRAServer.app import create_app  # noqa: E402
from SRAServer.config import ServerConfig  # noqa: E402
from SRACore.services import app_context, backend_service, cache_service  # noqa: E402
from SRACore.services import config_service as configs_service  # noqa: E402
from SRACore.services import setting_service  # noqa: E402
from SRAServer.controllers import task as task_controller  # noqa: E402

_BASE_URL = "http://127.0.0.1:8000"


@contextmanager
def build_server(
    tmp_dir: Path, access_token: str = "", visitor_mode: bool = False
) -> Iterator[TestClient]:
    """构造指向临时数据目录的测试客户端。

    除落盘路径外，同时替换 ``AppContext`` 初始化会触碰的真实位置（AppDataDir / ConfigsDir /
    CacheDir / settings.json / 截图路径 / 日志文件），使测试完全不读写用户的 ``%APPDATA%/SRA``。
    """
    configs_dir = tmp_dir / "configs"
    patches: list[tuple[Any, str, Any]] = [
        (cache_service, "CACHE_JSON", tmp_dir / "cache.json"),
        (configs_service, "ConfigsDir", configs_dir),
        (data_persister, "ConfigsDir", configs_dir),
        (task_controller, "ConfigsDir", configs_dir),
        (app_context, "AppDataDir", tmp_dir / "appdata"),
        (app_context, "ConfigsDir", configs_dir),
        (app_context, "CacheDir", tmp_dir / "cache"),
        (setting_service, "SettingsJson", tmp_dir / "settings.json"),
        (backend_service, "_SCREENSHOT_PATH", tmp_dir / "cache" / "screenshot.jpg"),
        (
            app_context,
            "setup_logger",
            partial(sra_logger.setup_logger, path=str(tmp_dir / "log" / "SRA{time:YYYYMMDD}.log")),
        ),
    ]
    saved = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
    for obj, name, value in patches:
        setattr(obj, name, value)
    try:
        config = ServerConfig.load(
            host="127.0.0.1",
            port=5073,
            webui=False,
            access_token=access_token,
            visitor_mode=visitor_mode,
        )
        app = create_app(config)
        with TestClient(app, base_url=_BASE_URL) as client:
            yield client
    finally:
        for obj, name, value in saved:
            setattr(obj, name, value)


@pytest.fixture(scope="module")
def client(tmp_path_factory) -> Iterator[TestClient]:
    with build_server(tmp_path_factory.mktemp("sra_server")) as test_client:
        yield test_client


# ── App ──


def test_system_info(client: TestClient) -> None:
    payload = client.get("/api/app/system-info").json()
    assert payload["success"] is True
    assert payload["data"]["version"]
    assert payload["data"]["processorCount"] >= 1


def test_phrases(client: TestClient) -> None:
    payload = client.get("/api/app/phrases").json()
    assert payload["success"] is True
    assert isinstance(payload["data"], list)
    assert payload["data"]


def test_background_is_jpeg(client: TestClient) -> None:
    response = client.get("/api/app/background")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


# ── Configs ──


def test_configs_crud(client: TestClient) -> None:
    name = "ApiTestCfg"

    created = client.post(f"/api/configs/{name}")
    assert created.status_code == 200
    assert created.json() == {"success": True, "message": "success", "data": name}

    names = client.get("/api/configs").json()["data"]
    assert name in names

    fetched = client.get(f"/api/configs/{name}").json()
    assert fetched["success"] is True
    assert set(fetched["data"]).issuperset(
        {"name", "startGame", "trailblazePower", "receiveRewards", "cosmicStrife", "missionAccomplished"}
    )

    updated = client.put(f"/api/configs/{name}", json={"name": name, "startGame": {"enabled": False}})
    assert updated.json()["success"] is True

    deleted = client.delete(f"/api/configs/{name}")
    assert deleted.json()["success"] is True
    assert name not in client.get("/api/configs").json()["data"]

    # 删除后列表不再包含该配置
    assert client.get(f"/api/configs/{name}").status_code == 404


def test_configs_invalid_and_duplicate_name(client: TestClient) -> None:
    assert client.post("/api/configs/bad:name").status_code == 400

    name = "ApiDupCfg"
    assert client.post(f"/api/configs/{name}").status_code == 200
    assert client.post(f"/api/configs/{name}").status_code == 409
    client.delete(f"/api/configs/{name}")


def test_configs_missing_returns_404(client: TestClient) -> None:
    assert client.get("/api/configs/NoSuchConfig").status_code == 404
    assert client.put("/api/configs/NoSuchConfig", json={}).status_code == 404
    assert client.delete("/api/configs/NoSuchConfig").status_code == 404


# ── Settings ──


def test_settings_get_and_patch(client: TestClient) -> None:
    data = client.get("/api/settings").json()["data"]
    assert set(data) == {"general", "display", "update", "advanced", "notification"}

    section = next(iter(data))
    field = next(iter(data[section]))
    value = data[section][field]

    patched = client.put("/api/settings", json={section: {field: value}})
    assert patched.status_code == 200
    body = patched.json()
    assert body["success"] is True
    assert f"{section}.{field}" in body["data"]


def test_settings_empty_patch_returns_400(client: TestClient) -> None:
    assert client.put("/api/settings", json={}).status_code == 400
    assert client.put("/api/settings", json={"general": {"noSuchField": 1}}).status_code == 400


# ── Task ──


def test_task_status_shape(client: TestClient) -> None:
    body = client.get("/api/task/status").json()
    assert body["success"] is True
    assert {
        "session_id",
        "pid",
        "mode",
        "status",
        "configs",
        "unit",
        "error",
        "progress",
    }.issubset(body["data"])


def test_task_stop_when_idle(client: TestClient) -> None:
    body = client.post("/api/task/stop").json()
    assert body["success"] is False


def test_task_request_accepts_client_field_names() -> None:
    """请求体模型须接受 WebUI 的 camelCase 与桌面端的 PascalCase 字段名。

    回归：字段名不匹配时 ``extra="allow"`` 会静默吞掉多余键，``config_name`` 退化为 None，
    导致 ``/api/task/run`` 误跑「全部配置」。
    """
    from SRAServer.schemas.requests import RunRequest, SingleTaskRequest

    camel = RunRequest.model_validate({"configName": "默认配置", "persist": True})
    assert camel.config_name == "默认配置"
    assert camel.persist is True

    pascal = RunRequest.model_validate({"Config": {"name": "x"}, "Persist": True})
    assert pascal.config == {"name": "x"}
    assert pascal.persist is True

    snake = RunRequest.model_validate({"config_name": "c", "config": {"name": "y"}})
    assert snake.config_name == "c"
    assert snake.config == {"name": "y"}

    single_camel = SingleTaskRequest.model_validate({"taskName": "StartGameTask", "configName": "默认配置"})
    assert single_camel.task_name == "StartGameTask"
    assert single_camel.config_name == "默认配置"

    single_pascal = SingleTaskRequest.model_validate({"TaskName": "StartGameTask"})
    assert single_pascal.task_name == "StartGameTask"
    assert single_pascal.config_name is None


# ── Operator / Extensions / Backend logs ──


def test_operator_list_and_help(client: TestClient) -> None:
    methods = client.get("/api/operator/list").json()["data"]
    assert "click_point" in methods

    help_body = client.get("/api/operator/help/click_point").json()
    assert help_body["success"] is True
    assert help_body["data"]["method"] == "click_point"

    assert client.get("/api/operator/help/not_a_method").json()["success"] is False


def test_operator_call_requires_method(client: TestClient) -> None:
    assert client.post("/api/operator/call", json={"method": ""}).status_code == 400


def test_extensions_list_and_unknown(client: TestClient) -> None:
    assert isinstance(client.get("/api/extensions").json()["data"], list)
    assert client.get("/api/extensions/not-an-extension/schema").json()["success"] is False


def test_backend_logs(client: TestClient) -> None:
    body = client.get("/api/backend/logs", params={"count": 10}).json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


# ── 鉴权 ──


def test_auth_disabled_allows_all(tmp_path: Path) -> None:
    with build_server(tmp_path, access_token="") as test_client:
        assert test_client.get("/api/configs").status_code == 200


def test_auth_enforced(tmp_path: Path) -> None:
    token = "secret-token"
    with build_server(tmp_path, access_token=token) as test_client:
        assert test_client.get("/api/configs").status_code == 401

        header_ok = test_client.get("/api/configs", headers={"X-Access-Token": token})
        assert header_ok.status_code == 200

        query_ok = test_client.get("/api/configs", params={"access_token": token})
        assert query_ok.status_code == 200

        # 匿名端点
        assert test_client.post("/api/auth", json={"token": token}).status_code == 200
        assert test_client.post("/api/auth", json={"token": "wrong"}).status_code == 401
        assert test_client.get("/api/app/background").status_code == 200


def test_auth_endpoint_without_configured_token(tmp_path: Path) -> None:
    with build_server(tmp_path, access_token="") as test_client:
        body = test_client.post("/api/auth", json={}).json()
        assert body["success"] is True