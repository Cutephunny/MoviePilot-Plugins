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
    plugin_desc = "接收消息通知并转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.3"
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
    _onlyonce = False  # 参考 Bark 的 onlyonce 逻辑

    def init_plugin(self, config: dict = None):
        """
        初始化配置
        """
        if config:
            self._enabled = config.get("enabled")
            self._google_chat_url = config.get("google_chat_url")
            self._msgtypes = config.get("msgtypes") or []
            self._onlyonce = config.get("onlyonce")

        # 参考 Bark 逻辑：如果启用状态且勾选了测试，则立即运行一次
        if self._enabled and self._onlyonce:
            # 立即重置测试开关，防止重复测试
            self._onlyonce = False
            # 发送一个带图片的测试通知
            self._do_send(
                title="GoogleChat配置测试通知",
                text="GoogleChat配置已保存。这是一条带图片的测试消息。图片在上方，文字在下方，并且图片尺寸已经缩小。",
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
        image = msg_body.get("image")  # 日志显示 Notification 对象包含 image
        
        return self._do_send(title=title, text=text, image_url=image)

    def _do_send(self, title: str, text: str, image_url: str = None) -> schemas.Response:
        """
        执行底层发送：解决图片布局（上方）和尺寸太大（=220x）
        """
        try:
            # 如果有图片，使用 cardsV2 格式的 TextParagraph Markdown 语法解决布局和尺寸问题
            if image_url:
                # Markdown 解析器中，普通的换行通常会被解析为 Markdown 单行。
                # 如果需要换行，可以使用 replace('\n', '  \n') 两个空格加换行。

                markdown_text = text.replace('\n', '  \n')

                # Markdown 拼接：
                # 1. 封面图片 ![TMDB封面](image_url =220x) (指定宽度为 220 像素)
                # 2. 消息标题 *{title}*
                # 3. 消息详情

                full_markdown = f"![TMDB封面]({image_url} =220x)\n\n"
                full_markdown += f"*{title}*\n\n"
                full_markdown += markdown_text

                payload = {
                    "cardsV2": [{
                        "cardId": "moviepilot_notification",
                        "card": {
                            "header": {
                                # Header 保持，作为副标题
                                "subtitle": "MoviePilot 通知",
                                "title": title
                            },
                            "sections": [{
                                "widgets": [
                                    # 这里使用一个 TextParagraph，完美的 Markdown
                                    {"textParagraph": {"text": full_markdown}}
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

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        # 生成通知类型多选框
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
            "onlyonce": False, # 测试开关默认不勾选
            "google_chat_url": "",
            "msgtypes": []
        }

    # --- get_command 保持空，防止抽象类实例化报错 ---
    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_page(self) -> List[dict]:
        return []

    def stop_service(self):
        pass
