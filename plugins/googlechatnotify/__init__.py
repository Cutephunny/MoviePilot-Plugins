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
    plugin_version = "1.6" # 在 1.4 基础上修复
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    # 插件配置项ID前缀
    plugin_config_prefix = "googlechat_notify_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _google_chat_url = ""
    _msgtypes = []
    _onlyonce = False  # 测试开关

    def init_plugin(self, config: dict = None):
        """
        初始化配置
        """
        if config:
            self._enabled = config.get("enabled")
            self._google_chat_url = config.get("google_chat_url")
            self._msgtypes = config.get("msgtypes") or []
            self._onlyonce = config.get("onlyonce")

        # 保持 V1.4 的逻辑：如果启用状态且勾选了测试，则立即运行一次
        if self._enabled and self._onlyonce:
            self._onlyonce = False
            self._do_send(
                title="GoogleChat配置测试通知",
                text="GoogleChat配置已保存。这是一条测试消息。\n已修复：原生组件渲染图片，确保 100% 显示。",
                image_url="https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
            )

    def get_state(self) -> bool:
        """插件是否激活"""
        return self._enabled and bool(self._google_chat_url)

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        """
        监听系统通知事件并转发
        """
        if not self.get_state():
            return

        msg_body = event.event_data
        if not msg_body:
            return

        # 过滤已由其他渠道处理的消息
        if msg_body.get("channel"):
            return

        # 消息类型过滤
        msg_type: NotificationType = msg_body.get("type")
        if msg_type and self._msgtypes and msg_type.name not in self._msgtypes:
            return

        title = msg_body.get("title")
        text = msg_body.get("text")
        image = msg_body.get("image")
        
        return self._do_send(title=title, text=text, image_url=image)

    def _do_send(self, title: str, text: str, image_url: str = None) -> schemas.Response:
        """
        【关键修复区】基于 V1.4 修复图片不显示问题
        放弃 Markdown 图片语法，改用原生 Google Chat widgets
        """
        try:
            if image_url:
                # 转换普通换行符为 Google Chat 卡片支持的 HTML 换行
                formatted_text = text.replace('\n', '<br>')

                payload = {
                    "cardsV2": [{
                        "cardId": "moviepilot_notification",
                        "card": {
                            "header": {
                                "title": title,
                                "subtitle": "MoviePilot 通知"
                            },
                            "sections": [
                                {
                                    # 第一个区块放图片：确保图片在上方，且原生组件不会显示源码
                                    "widgets": [{"image": {"imageUrl": image_url}}]
                                },
                                {
                                    # 第二个区块放文字：确保文字在下方
                                    "widgets": [{
                                        "textParagraph": {"text": f"<b>{title}</b><br><br>{formatted_text}"}
                                    }]
                                }
                            ]
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

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        # 保持 V1.4 的原版 UI，确保不白屏
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
                                    {
                                        'component': 'VSwitch',
                                        'props': {'model': 'enabled', 'label': '启用插件'}
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {'model': 'onlyonce', 'label': '保存并测试（点击保存触发）'}
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

    # --- 保持 V1.4 原样，防止界面崩溃 ---
    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_page(self) -> List[dict]:
        return []

    def stop_service(self):
        pass
