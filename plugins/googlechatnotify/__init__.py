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

    # 私有属性
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

        # 模仿 MeoW 逻辑：如果勾选了立即运行测试
        if self._enabled and self._onlyonce:
            logger.info(f"[{self.plugin_name}] 测试插件，立即运行一次")
            self._onlyonce = False
            # 更新配置以重置开关状态
            self.update_config({
                "enabled": self._enabled,
                "onlyonce": self._onlyonce,
                "google_chat_url": self._google_chat_url,
                "msgtypes": self._msgtypes
            })
            # 执行测试发送
            self._do_send(
                title="GoogleChat 测试通知",
                text="✅ 插件配置已保存！\n布局预览：图片在上，文字在下。\n换行测试：\n这是第二行内容。",
                image_url=self.plugin_icon
            )

    def get_state(self) -> bool:
        return self._enabled and bool(self._google_chat_url)

    def _do_send(self, title: str, text: str, image_url: str = None) -> schemas.Response:
        """核心发送逻辑：原生组件实现图上文下"""
        try:
            if image_url:
                # 使用 Cards V2 官方组件
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
                                    # Section 1: 封面图片
                                    "widgets": [{"image": {"imageUrl": image_url}}]
                                },
                                {
                                    # Section 2: 详情文字
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
                payload = {"text": f"*{title}*\n{text}"}

            headers = {"Content-Type": "application/json; charset=UTF-8"}
            res = requests.post(self._google_chat_url, headers=headers, data=json.dumps(payload), timeout=10)
            return schemas.Response(success=True) if res.status_code == 200 else schemas.Response(success=False)
        except Exception as e:
            logger.error(f"发送失败: {str(e)}")
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
        """模仿 MeoW 风格的 UI 布局"""
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

    def get_command(self) -> List[Dict[str, Any]]:
        """卡片底部的独立测试按钮"""
        return [{
            "id": "test_cmd",
            "title": "发送测试通知",
            "description": "点击后立即向 Google Chat 发送测试消息",
            "display": "button",
            "color": "primary"
        }]

    def test_cmd(self, **kwargs):
        """对应 get_command 的 id"""
        return self._do_send(
            title="测试按钮通知",
            text="✅ 这是通过卡片按钮触发的测试。",
            image_url=self.plugin_icon
        )

    def get_page(self) -> List[dict]: return []
    def stop_service(self): pass
