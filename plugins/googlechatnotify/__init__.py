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
    plugin_desc = "接收消息通知并以纯文字形式转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.7"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    plugin_config_prefix = "googlechat_notify_"
    plugin_order = 30
    auth_level = 1

    # 私有属性
    _enabled = False
    _google_chat_url = ""
    _msgtypes = []
    _onlyonce = False 

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._google_chat_url = config.get("google_chat_url")
            self._msgtypes = config.get("msgtypes") or []
            self._onlyonce = config.get("onlyonce")

        # 保存并测试逻辑
        if self._enabled and self._onlyonce:
            self._onlyonce = False
            self._do_send(
                title="GoogleChat 纯文字测试",
                text="✅ 配置已保存。这是一条纯文字测试消息，去掉了图片以确保显示效果最稳定。"
            )

    def get_state(self) -> bool:
        return self._enabled and bool(self._google_chat_url)

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        if not self.get_state():
            return

        msg_body = event.event_data
        if not msg_body or msg_body.get("channel"):
            return

        msg_type: NotificationType = msg_body.get("type")
        if msg_type and self._msgtypes and msg_type.name not in self._msgtypes:
            return

        title = msg_body.get("title")
        text = msg_body.get("text")
        
        return self._do_send(title=title, text=text)

    def _do_send(self, title: str, text: str) -> schemas.Response:
        """
        纯文本发送逻辑：最简单、最稳定
        """
        try:
            if not self._google_chat_url:
                return schemas.Response(success=False, message="URL 未配置")

            # 构造纯文本 Payload
            # Google Chat 支持基本的 Markdown：*加粗*
            full_content = f"*{title}*\n\n{text}"
            payload = {"text": full_content}

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
            logger.error(f"[GoogleChat] 发送失败: {str(e)}")
            return schemas.Response(success=False, message=str(e))

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
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件'}}
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {'component': 'VSwitch', 'props': {'model': 'onlyonce', 'label': '保存并测试'}}
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
                                            'label': 'Webhook URL',
                                            'placeholder': 'https://chat.googleapis.com/v1/spaces/...',
                                            'clearable': True
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
            "onlyonce": False,
            "google_chat_url": "",
            "msgtypes": []
        }

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_page(self) -> List[dict]:
        return []

    def stop_service(self):
        pass
