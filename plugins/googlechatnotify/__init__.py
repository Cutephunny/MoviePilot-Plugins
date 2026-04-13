import requests
import json
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.log import logger
from app import schemas
from app.core.event import eventmanager, Event
from app.schemas.types import EventType, NotificationType

class GoogleChatNotify(_PluginBase):
    # --- 插件元数据 ---
    plugin_name = "GoogleChat通知插件"
    plugin_desc = "接收消息通知并转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.4"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    plugin_config_prefix = "googlechat_notify_"
    plugin_order = 30
    auth_level = 1

    # 配置变量
    _enabled = False
    _google_chat_url = ""
    _msgtypes = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._google_chat_url = config.get("google_chat_url")
            self._msgtypes = config.get("msgtypes") or []

    def get_state(self) -> bool:
        return self._enabled and bool(self._google_chat_url)

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        """监听系统通知并转发"""
        if not self.get_state():
            return

        msg_body = event.event_data
        if not msg_body or msg_body.get("channel"):
            return

        # 消息类型过滤
        msg_type: NotificationType = msg_body.get("type")
        if msg_type and self._msgtypes and msg_type.name not in self._msgtypes:
            return

        title = msg_body.get("title")
        text = msg_body.get("text")
        image = msg_body.get("image")  # 获取通知中的图片链接
        
        return self._do_send(title=title, text=text, image_url=image)

    def _do_send(self, title: str, text: str, image_url: str = None) -> schemas.Response:
        """核心发送逻辑：图片在上，文字在下"""
        try:
            if not self._google_chat_url:
                return schemas.Response(success=False, message="未配置 Webhook URL")

            if image_url:
                # 使用 Cards V2 确保布局：图片 section 在上，文字 section 在下
                payload = {
                    "cardsV2": [{
                        "cardId": "moviepilot_notification",
                        "card": {
                            "header": {
                                "title": title,
                                "subtitle": "MoviePilot 通知",
                                "imageUrl": "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png",
                                "imageType": "CIRCLE"
                            },
                            "sections": [
                                {
                                    # 布局：图片在上
                                    "widgets": [{"image": {"imageUrl": image_url}}]
                                },
                                {
                                    # 布局：文字在下
                                    "widgets": [{
                                        "textParagraph": {
                                            "text": f"<b>{title}</b><br><br>{text.replace('\n', '<br>')}"
                                        }
                                    }]
                                }
                            ]
                        }
                    }]
                }
            else:
                # 纯文字简单模式
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
            logger.error(f"[{self.plugin_name}] 发送失败: {str(e)}")
            return schemas.Response(success=False, message=str(e))

    def test(self, **kwargs) -> schemas.Response:
        """测试按钮点击后调用的方法"""
        return self._do_send(
            title="独立按钮测试通知",
            text="✅ 恭喜！测试按钮运行正常。\n当前布局：图片在上，文字在下，尺寸已优化。",
            image_url="https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
        )

    def get_command(self) -> List[Dict[str, Any]]:
        """定义插件卡片上的独立按钮"""
        return [
            {
                "id": "test",
                "title": "发送测试通知",
                "description": "点击发送一条测试消息到 Google Chat",
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
        """必须返回空列表，否则插件可能无法显示"""
        return []

    def stop_service(self):
        pass
