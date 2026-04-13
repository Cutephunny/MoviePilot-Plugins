import requests
import json
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.log import logger
from app import schemas
from app.core.event import eventmanager, Event
from app.schemas.types import EventType, NotificationType

class GoogleChatNotify(_PluginBase):
    # --- 要求的插件元数据 ---
    plugin_name = "GoogleChat通知插件"
    plugin_desc = "接收 Webhook 信号并转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.3"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    # 配置项前缀
    plugin_config_prefix = "googlechat_notify_"
    plugin_order = 30
    auth_level = 1

    # 私有属性
    _enabled = False
    _google_chat_url = ""
    _msgtypes = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            self._google_chat_url = config.get("google_chat_url", "")
            self._msgtypes = config.get("msgtypes") or []

    def get_state(self) -> bool:
        return self._enabled and bool(self._google_chat_url)

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        """
        监听系统通知并转发
        """
        if not self.get_state():
            return

        msg_body = event.event_data
        if not msg_body:
            return

        # 过滤频道消息
        if msg_body.get("channel"):
            return

        # 检查消息类型过滤
        msg_type: NotificationType = msg_body.get("type")
        if msg_type and self._msgtypes and msg_type.name not in self._msgtypes:
            return

        title = msg_body.get("title")
        text = msg_body.get("text")
        image = msg_body.get("image") # 获取日志中的图片链接
        
        return self._do_send(title=title, text=text, image_url=image)

    def _do_send(self, title: str, text: str, image_url: str = None) -> schemas.Response:
        """
        执行发送：支持图片显示
        """
        try:
            # 如果有图片，使用 cardsV2 格式以渲染图片
            if image_url:
                payload = {
                    "cardsV2": [{
                        "cardId": "moviepilot_notification",
                        "card": {
                            "header": {
                                "title": title,
                                "subtitle": "MoviePilot 通知"
                            },
                            "sections": [{
                                "widgets": [
                                    {"textParagraph": {"text": text.replace('\n', '<br>')}},
                                    {"image": {"imageUrl": image_url}}
                                ]
                            }]
                        }
                    }]
                }
            else:
                # 只有文字时使用简单格式
                payload = {"text": f"*{title}*\n{text}"}

            headers = {"Content-Type": "application/json; charset=UTF-8"}
            res = requests.post(
                self._google_chat_url, 
                headers=headers, 
                data=json.dumps(payload), 
                timeout=10
            )
            
            if res.status_code == 200:
                return schemas.Response(success=True, message="发送成功")
            return schemas.Response(success=False, message=f"HTTP {res.status_code}")
        except Exception as e:
            logger.error(f"[GoogleChat] 异常: {str(e)}")
            return schemas.Response(success=False, message=str(e))

    def test_google_chat(self, **kwargs) -> schemas.Response:
        """测试按钮逻辑"""
        return self._do_send(
            title="测试通知", 
            text="✅ 插件配置正确！这是一条带图片的测试消息。",
            image_url="https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
        )

    def get_command(self) -> List[Dict[str, Any]]:
        """
        核心修复：确保按钮出现在插件卡片上
        """
        return [
            {
                "id": "test_google_chat",
                "title": "发送测试通知",
                "description": "发送一条带图片的测试消息",
                "display": "button",
                "color": "primary"
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        MsgTypeOptions = [{"title": item.value, "value": item.name} for item in NotificationType]
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                {'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件'}}
                            ]}
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                {'component': 'VTextField', 'props': {'model': 'google_chat_url', 'label': 'Webhook URL'}}
                            ]}
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                                {'component': 'VSelect', 'props': {'multiple': True, 'chips': True, 'model': 'msgtypes', 'label': '消息类型', 'items': MsgTypeOptions}}
                            ]}
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "google_chat_url": "",
            "msgtypes": []
        }

    def get_page(self) -> List[dict]:
        return []

    def stop_service(self):
        pass
