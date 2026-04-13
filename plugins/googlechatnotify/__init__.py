import requests
import json
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.log import logger
from app import schemas

class GoogleChatNotify(_PluginBase):
    # 插件元数据（必须与你的 manifest.json 一致）
    plugin_name = "GoogleChat通知插件"
    plugin_desc = "接收 Webhook 信号并转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.2"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    
    # 插件配置项ID前缀
    plugin_config_prefix = "googlechat_notify_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 1

    # 私有属性初始化
    _enabled = False
    _google_chat_url = ""
    _test_on_save = False  # 参考 Bark 的 onlyonce 逻辑

    def init_plugin(self, config: dict = None):
        """
        初始化配置：从配置字典中读取变量
        """
        if config:
            self._enabled = config.get("enabled")
            self._google_chat_url = config.get("google_chat_url")
            self._test_on_save = config.get("test_on_save")

        # 参考 Bark 逻辑：如果保存时勾选了测试，则立即运行一次
        if self._enabled and self._test_on_save:
            # 立即重置开关，防止重复测试
            self._test_on_save = False
            self._do_send("✅ Google Chat 配置已保存，这是一条测试通知。")

    def get_state(self) -> bool:
        """返回插件状态"""
        return self._enabled and bool(self._google_chat_url)

    def webhook_handler(self, text: str = None, title: str = None, content: str = None, url: str = None) -> schemas.Response:
        """
        供外部 Webhook 调用的接口
        """
        if not self.get_state():
            return schemas.Response(success=False, message="插件未启用或未配置URL")

        # 变量构造逻辑
        if text:
            msg_text = text
        else:
            msg_text = f"*{title or 'MoviePilot通知'}*\n{content or ''}"
            if url:
                msg_text += f"\n\n[查看详情]({url})"

        return self._do_send(msg_text)

    def _do_send(self, message: str) -> schemas.Response:
        """
        核心发送逻辑：严格对齐用户要求的构造方式
        """
        try:
            # 构造方式：Payload 使用 {"text": "..."}
            payload = {"text": message}
            # 构造方式：Header 严格定义 charset
            headers = {"Content-Type": "application/json; charset=UTF-8"}
            
            logger.info(f"[GoogleChat] 正在推送消息: {message[:20]}...")
            
            # 执行 POST
            response = requests.post(
                url=self._google_chat_url,
                headers=headers,
                data=json.dumps(payload), # 严格执行序列化
                timeout=10
            )
            
            if response.status_code == 200:
                return schemas.Response(success=True, message="发送成功")
            else:
                logger.error(f"[GoogleChat] 发送失败: {response.status_code}, {response.text}")
                return schemas.Response(success=False, message=f"HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"[GoogleChat] 请求异常: {str(e)}")
            return schemas.Response(success=False, message=str(e))

    def get_api(self) -> List[Dict[str, Any]]:
        """定义外部访问路径"""
        return [
            {
                "path": "/webhook",
                "endpoint": self.webhook_handler,
                "methods": ["GET", "POST"],
                "summary": "Google Chat Webhook转发",
                "description": "接收并转发通知到 Google Chat",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        UI 界面构造：完全对齐 BarkMsg 的嵌套风格，确保界面显示
        """
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
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用 Google Chat 推送',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'test_on_save',
                                            'label': '保存并测试（点击保存触发）',
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
                    }
                ]
            }
        ], {
            "enabled": False,
            "test_on_save": False,
            "google_chat_url": ""
        }

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass
