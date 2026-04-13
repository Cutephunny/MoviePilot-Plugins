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
    plugin_version = "1.5"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    plugin_config_prefix = "googlechat_notify_"
    plugin_order = 30
    auth_level = 1

    # 私有属性初始化
    _enabled = False
    _onlyonce = False
    _google_chat_url = ""
    _msgtypes = []

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._google_chat_url = config.get("google_chat_url")
            self._msgtypes = config.get("msgtypes") or []

        # 修复点：移除 self.update_config，改用直接判断
        if self._enabled and self._onlyonce:
            logger.info(f"[{self.plugin_name}] 正在执行保存后的自动测试...")
            self._do_send(
                title="GoogleChat 配置测试",
                text="✅ 插件配置已保存且初始化成功！\n布局：图片在上，文字在下。",
                image_url=self.plugin_icon
            )

    def get_state(self) -> bool:
        return self._enabled and bool(self._google_chat_url)

    def _do_send(self, title: str, text: str, image_url: str = None) -> schemas.Response:
        """核心发送逻辑"""
        try:
            if not self._google_chat_url:
                return schemas.Response(success=False, message="URL未配置")

            # 统一转换换行符为 HTML 换行
            formatted_text = text.replace('\n', '<br>')

            if image_url:
                # 原生 Cards V2 布局
                payload = {
                    "cardsV2": [{
                        "cardId": "mp_notification",
                        "card": {
                            "header": {
                                "title": title,
                                "subtitle": "MoviePilot 通知",
                                "imageUrl": self.plugin_icon,
                                "imageType": "CIRCLE"
                            },
                            "sections": [
                                {
                                    "widgets": [{"image": {"imageUrl": image_url}}]
                                },
                                {
                                    "widgets": [{
                                        "textParagraph": {
                                            "text": f"<b>{title}</b><br><br>{formatted_text}"
                                        }
                                    }]
                                }
                            ]
                        }
                    }]
                }
            else:
                payload = {"text": f"*{title}*\n{text}"}

            headers = {"Content-Type": "application/json; charset=UTF-8"}
            res = requests.post(self._google_chat_url, headers=headers, data=json.dumps(payload), timeout=10)
            return schemas.Response(success=True)
        except Exception as e:
            logger.error(f"[GoogleChat] 发送异常: {str(e)}")
            return schemas.Response(success=False, message=str(e))

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        if not self.get_state() or not event.event_data:
            return
        
        msg_body = event.event_data
        if msg_body.get("channel"): return

        msg_type: NotificationType = msg_body.get("type")
        if msg_type and self._msgtypes and msg_type.name not in self._msgtypes:
            return

        return self._do_send(
            title=msg_body.get("title"),
            text=msg_body.get("text"),
            image_url=msg_body.get("image")
        )

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """100% 模仿 MeoW 布局"""
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
                                'content': [{'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件'}}]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [{'component': 'VSwitch', 'props': {'model': 'onlyonce', 'label': '测试插件（立即运行）'}}]
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

    def get_command(self) -> List[Dict[str, Any]]:
        """定义卡片测试按钮"""
        return [{
            "id": "test_button",
            "title": "发送测试通知",
            "description": "点击发送测试消息",
            "display": "button",
            "color": "primary"
        }]

    def test_button(self, **kwargs):
        """按钮回调方法"""
        return self._do_send(
            title="手动测试成功",
            text="这是通过卡片底部的独立按钮触发的消息。",
            image_url=self.plugin_icon
        )

    def get_page(self) -> List[dict]: return []
    def stop_service(self): pass
