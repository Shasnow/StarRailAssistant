"""基于多模态大模型的视觉定位。

模板匹配对缩放、半透明遮罩和动态特效比较敏感，这里提供一条兜底链路：
把模板图与当前游戏截图一起发送给支持图像输入的对话模型，要求模型返回结构化 JSON
（是否命中、相对外接矩形、可信度、理由），由调用方换算成窗口坐标。

配置来自 ``settings.json`` 的 ``advanced.llmVision`` 段（前端设置页的“多模态视觉定位”）：:

    {
      "advanced": {
        "llmVision": {
          "enabled": true,
          "baseUrl": "https://api.openai.com/v1",
          "apiKey": "<加密后的值>",
          "model": "gpt-4o-mini",
          "timeout": 30,
          "proxyUrl": ""
        }
      }
    }

``baseUrl`` 指向 OpenAI 兼容的接口前缀，也可以直接写完整的 ``/chat/completions`` 地址。
``apiKey`` 由前端加密写入，服务端直接手填明文时按明文使用。
未启用或缺少 ``baseUrl`` / ``model`` 时，``IOperator.locate_with_llm`` 会直接返回 ``None``。
"""

from __future__ import annotations

import base64
import io
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger
from PIL import Image

from SRACore.util.encryption import decryptor

if TYPE_CHECKING:
    from SRACore.models.app_settings import AppSettings


def _decrypt_api_key(stored: str) -> str:
    """读取 API Key：前端用 DPAPI 加密存储，解密失败时按明文处理（服务端手填场景）。"""
    if not stored:
        return ""
    return decryptor(stored) or stored


class LlmVisionError(RuntimeError):
    """LLM 视觉定位调用失败（未配置、请求失败或返回内容无法解析）。"""


@dataclass(frozen=True)
class LlmVisionResult:
    """模型返回的结构化定位结果，坐标为相对发送图像的 0~1 比例。"""

    found: bool
    box: tuple[float, float, float, float] | None = None
    confidence: float | None = None
    reason: str = ""
    raw: str = ""


class LlmVision:
    """多模态 LLM 视觉定位客户端。

    通过 ``LlmVision.from_settings()`` 读取 ``settings.json`` 的 ``llmVision`` 段构造，
    或直接传入参数实例化；调用 ``locate()`` 发送图片并拿回结构化结果。
    """

    _SYSTEM_PROMPT = (
        "你是游戏界面视觉定位助手。用户会依次给出模板图（TARGET）和当前游戏截图（SCREENSHOT），"
        "请判断 SCREENSHOT 中是否存在与 TARGET 相同或高度相似的界面元素，并给出该元素的外接矩形。"
        "坐标使用相对 SCREENSHOT 宽高的 0~1 比例。"
        "只输出一个 JSON 对象，不要输出 Markdown 代码块、解释或任何多余文本。"
    )

    _RESULT_FORMAT = (
        '{"success": true, "data": { "box": [x1, y1, x2, y2], "confidence": 0.0 }, '
        '"message": "简短判断依据"}；未找到时 success 为 false、data 为 null'
    )

    _JSON_OBJECT = re.compile(r"\{.*\}", re.S)
    _FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")

    def __init__(self,
                 base_url: str = "",
                 api_key: str = "",
                 model: str = "",
                 timeout: float = 30.0,
                 max_side: int = 1280,
                 jpeg_quality: int = 85,
                 proxy_url: str = "",
                 response_format: dict[str, Any] | None = None,
                 extra_headers: dict[str, str] | None = None,
                 extra_body: dict[str, Any] | None = None,
                 is_enabled: bool = True):
        self.base_url = base_url.strip() or ""
        self.api_key = api_key.strip() or ""
        self.model = model.strip() or ""
        self.timeout = timeout
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality
        self.proxy_url = proxy_url.strip() or ""
        # None 表示使用默认的 JSON 输出模式；空字典表示不发送该字段（部分服务不支持）
        self.response_format = {"type": "json_object"} if response_format is None else response_format
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}
        self.is_enabled = is_enabled

    @property
    def enabled(self) -> bool:
        """设置项已开启且具备调用条件（本地部署可以不填 api_key）。"""
        return self.is_enabled and bool(self.base_url and self.model)

    @classmethod
    def from_settings(cls, settings: "AppSettings") -> "LlmVision":
        """从 ``settings.json`` 的 ``advanced.llmVision`` 段构造实例。"""
        config = settings.Advanced.LlmVision
        return cls(
            base_url=config.baseUrl,
            api_key=_decrypt_api_key(config.EncryptedApiKey),
            model=config.model,
            timeout=config.timeout,
            proxy_url=config.proxyUrl,
            is_enabled=config.isEnabled,
        )

    def locate(self,
               template: Image.Image,
               screenshot: Image.Image,
               *,
               description: str = "") -> LlmVisionResult:
        """调用 LLM 视觉定位模型，返回结构化定位结果。

        Args:
            template: 模板图片。
            screenshot: 当前游戏画面（建议传窗口截图，不要传整屏）。
            description: 额外的目标说明，会拼进提示词。

        Returns:
            LlmVisionResult: ``box`` 为相对发送图像宽高的 0~1 比例坐标。

        Raises:
            LlmVisionError: 未配置、请求失败或返回内容无法解析。
        """
        if not self.enabled:
            raise LlmVisionError("未配置多模态 LLM：缺少 baseUrl 或 model")

        template_url, _ = self._encode_image(template, max_side=self.max_side, quality=self.jpeg_quality)
        screenshot_url, screenshot_size = self._encode_image(screenshot, max_side=self.max_side,
                                                             quality=self.jpeg_quality)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(template_url, screenshot_url, description),
            "temperature": 0,
        }
        if self.response_format:
            payload["response_format"] = self.response_format
        payload.update(self.extra_body)

        headers = {"Content-Type": "application/json", "User-Agent": "StarRailAssistant/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)

        status, body, error = self._post_json(self._chat_completions_url(self.base_url), payload, headers,
                                              timeout=self.timeout, proxy_url=self.proxy_url)
        if not 200 <= status < 300 or error:
            raise LlmVisionError(f"请求失败（HTTP {status}）：{error or body[:200]}")

        try:
            response = json.loads(body)
        except json.JSONDecodeError as parse_error:
            raise LlmVisionError(f"响应不是合法 JSON：{body[:200]}") from parse_error
        content = self._extract_content(response)
        return self._parse_result(self._load_json_object(content), screenshot_size, content)

    def _build_messages(self, template_url: str, screenshot_url: str, description: str) -> list[dict[str, Any]]:
        instruction = "请在 SCREENSHOT 中定位与 TARGET 相同或高度相似的界面元素。"
        if description.strip():
            instruction += f"\n目标说明：{description.strip()}"
        instruction += f"\n只返回 JSON，格式：{self._RESULT_FORMAT}"
        return [
            {"role": "system", "content": self._SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": instruction},
                {"type": "text", "text": "【模板图 TARGET】"},
                {"type": "image_url", "image_url": {"url": template_url}},
                {"type": "text", "text": "【游戏截图 SCREENSHOT】"},
                {"type": "image_url", "image_url": {"url": screenshot_url}},
            ]},
        ]

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        url = base_url.strip().rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        return url + "/chat/completions"

    @staticmethod
    def _encode_image(image: Image.Image, *, max_side: int, quality: int) -> tuple[str, tuple[int, int]]:
        """编码成 data URL，返回 (url, 发送时的图像尺寸)。

        大图按长边缩放到 ``max_side``，既控制请求体积，也避免超出模型的图像分辨率上限；
        归一化坐标在等比缩放后仍然一致，因此调用方无需关心缩放比例。
        """
        rgb = image.convert("RGB")
        if max_side > 0 and max(rgb.size) > max_side:
            scale = max_side / max(rgb.size)
            rgb = rgb.resize((max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale))),
                             Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        rgb.save(buffer, format="JPEG", quality=max(1, min(95, quality)))
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}", rgb.size

    @staticmethod
    def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], *,
                   timeout: float, proxy_url: str = "") -> tuple[int, str, str]:
        """发送 JSON POST 请求，返回 (状态码, 响应体, 错误描述)，不抛网络异常。"""
        logger.debug(f"POST {url}")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        opener = urllib.request.build_opener()
        if proxy_url:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
        try:
            with opener.open(request, timeout=timeout) as response:
                return response.status, response.read().decode("utf-8", errors="replace"), ""
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", errors="replace"), "http error"
        except urllib.error.URLError as error:
            return 0, "", f"url error: {error.reason}"
        except Exception as error:  # 超时、连接被重置等
            return 0, "", f"{type(error).__name__}: {error}"

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        """从 chat-completions 响应中取出文本内容。"""
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmVisionError(f"响应缺少 choices：{json.dumps(response, ensure_ascii=False)[:200]}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            # 部分厂商把 content 拆成多段
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            raise LlmVisionError("模型返回内容为空")
        return content

    @classmethod
    def _load_json_object(cls, text: str) -> dict[str, Any]:
        """解析模型输出中的 JSON 对象，兼容 ```json 代码块与前后多余文字。"""
        candidate = cls._FENCE.sub("", text.strip())
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            match = cls._JSON_OBJECT.search(text)
            if match is None:
                raise LlmVisionError(f"模型未返回 JSON：{text[:200]}") from None
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError as error:
                raise LlmVisionError(f"模型返回的 JSON 无法解析：{error}") from error
        if not isinstance(data, dict):
            raise LlmVisionError("模型返回的 JSON 不是对象")
        return data

    def _parse_result(self, data: dict[str, Any], image_size: tuple[int, int], raw: str) -> LlmVisionResult:
        """把模型返回的信封（success/data/message）转成定位结果。"""
        payload = data.get("data") if isinstance(data.get("data"), dict) else {}
        box = self._coerce_box(payload.get("box") or payload.get("bbox") or payload.get("boundingBox")  # pyright: ignore[reportOptionalMemberAccess]
                               or data.get("box"), image_size)
        success = data.get("success")
        if success is None:  # 兼容直接返回 found/box 的模型
            success = data.get("found", box is not None)
        return LlmVisionResult(
            found=bool(success) and box is not None,
            box=box,
            confidence=self._coerce_confidence(payload.get("confidence", data.get("confidence"))),  # pyright: ignore[reportOptionalMemberAccess]
            reason=str(data.get("message") or data.get("reason") or "").strip(),
            raw=raw,
        )

    @staticmethod
    def _coerce_box(value: Any, image_size: tuple[int, int]) -> tuple[float, float, float, float] | None:
        """把模型给出的矩形换算成 0~1 比例坐标，并做顺序与范围校验。"""
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return None
        try:
            coords = [float(item) for item in value]
        except (TypeError, ValueError):
            return None
        width, height = image_size
        if width <= 0 or height <= 0:
            return None
        max_value = max(abs(item) for item in coords)
        if 2.0 < max_value <= max(width, height) * 1.05:
            # 有的模型会直接返回像素坐标，按发送尺寸归一化；
            # 略大于 1 的值更可能是潦草的归一化坐标，仍按比例处理后裁剪
            coords = [coords[0] / width, coords[1] / height, coords[2] / width, coords[3] / height]
        x1, y1, x2, y2 = coords
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        x1, y1 = max(0.0, min(1.0, x1)), max(0.0, min(1.0, y1))
        x2, y2 = max(0.0, min(1.0, x2)), max(0.0, min(1.0, y2))
        if x2 - x1 <= 0 or y2 - y1 <= 0:
            return None
        return x1, y1, x2, y2

    @staticmethod
    def _coerce_confidence(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number > 1.0:
            number /= 100.0  # 兼容百分数
        return max(0.0, min(1.0, number))
