import requests
import json
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.log import logger
from app import schemas
from app.core.event import eventmanager, Event
from app.schemas.types import EventType, NotificationType

class GoogleChatNotify(_PluginBase):
    # 插件元数据
    plugin_name = "GoogleChat通知插件"
    plugin_desc = "接收 Webhook 信号并转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.3"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    # 必须与目录名和前缀一致
    plugin_config_prefix = "googlechat_notify_"
    plugin_order = 30
    auth_level = 1

    # 私有属性
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
        """
        监听 MoviePilot 系统通知事件
        """
        if not self.get_state():
            return

        msg_body = event.event_data
        if not msg_body:
            return

        # 过滤已由其他渠道处理的消息
        if msg_body.get("channel"):
            return

        # 检查消息类型是否在用户勾选的范围内
        msg_type: NotificationType = msg_body.get("type")
        if msg_type and self._msgtypes and msg_type.name not in self._msgtypes:
            return

        title = msg_body.get("title")
        text = msg_body.get("text")
        
        # 构造并发送
        formatted_text = f"*{title}*\n{text}"
        return self._do_send(formatted_text)

    def _do_send(self, message: str) -> schemas.Response:
        """执行底层发送"""
        try:
            payload = {"text": message}
            headers = {"Content-Type": "application/json; charset=UTF-8"}
            res = requests.post(self._google_chat_url, headers=headers, data=json.dumps(payload), timeout=10)
            if res.status_code == 200:
                return schemas.Response(success=True, message="发送成功")
            return schemas.Response(success=False, message=f"HTTP {res.status_code}")
        except Exception as e:
            logger.error(f"[GoogleChat] 发送失败: {str(e)}")
            return schemas.Response(success=False, message=str(e))

    def test_google_chat(self, **kwargs) -> schemas.Response:
        """测试按钮触发"""
        return self._do_send("🚀 这是一条来自 MoviePilot 的 Google Chat 测试消息")

    def get_command(self) -> List[Dict[str, Any]]:
        """定义插件卡片上的按钮"""
        return [
            {
                "id": "test_google_chat",
                "title": "发送测试",
                "description": "向 Google Chat 发送一条测试消息",
                "display": "button",
                "color": "primary"
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        # 生成消息类型多选列表
        MsgTypeOptions = []
        for item in NotificationType:
            MsgTypeOptions.append({"title": item.value, "value": item.name})

        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {'model': 'enabled', 'label': '启用插件'}
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'google_chat_url',
                                            'label': 'Google Chat Webhook URL',
                                            'placeholder': 'https://chat.googleapis.com/v1/spaces/...',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': True,
                                            'chips': True,
                                            'model': 'msgtypes',
                                            'label': '消息类型',
                                            'items': MsgTypeOptions
                                        }
                                    }
                                ]
                            }
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
        """必须实现的抽象方法"""
        return []

    def stop_service(self):
        pass
