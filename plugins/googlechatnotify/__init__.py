import requests
import json
from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple
from app.log import logger
from app import schemas

class GoogleChatNotify(_PluginBase):
    # 插件元数据
    plugin_name = "Google Chat 通知插件"
    plugin_desc = "接收 MoviePilot 通知并转发至 Google Chat。"
    plugin_icon = "https://raw.githubusercontent.com/Cutephunny/MoviePilot-Plugins/main/icons/Google_A.png"
    plugin_version = "1.0"
    plugin_author = "Gemini"
    author_url = "https://github.com"
    plugin_config_prefix = "googlechat_notify_"
    plugin_order = 30
    auth_level = 1

    # 配置变量初始化
    _enabled = False
    _google_chat_url = ""

    def init_plugin(self, config: dict = None):
        """初始化配置"""
        if config:
            self._enabled = config.get("enabled")
            self._google_chat_url = config.get("google_chat_url", "")

    def send_notify(self, text: str = None, title: str = None, content: str = None, url: str = None) -> schemas.Response:
        """
        MoviePilot 核心通知入口
        当 MP 产生下载完成、入库等通知时，会自动调用此函数
        """
        if not self._enabled:
            return schemas.Response(success=False, message="插件未启用")

        if not self._google_chat_url:
            return schemas.Response(success=False, message="未配置 Google Chat URL")

        # --- 变量校验与处理 ---
        # 如果 text 存在（通常是简单 Webhook 传入），直接使用
        if text:
            msg_text = text
        else:
            # 如果是 MP 内部通知，通常包含 title 和 content
            # 使用 Markdown 粗体语法 (*) 增强标题显示效果
            msg_text = f"*{title or 'MoviePilot 通知'}*\n{content or ''}"
            if url:
                msg_text += f"\n\n查看详情: {url}"

        # 执行发送
        return self._do_send(msg_text)

    def _do_send(self, message_text: str) -> schemas.Response:
        """
        底层发送逻辑：严格参考 Google Chat 构造方式
        """
        try:
            # 1. 构造 JSON Payload
            app_message = {"text": message_text}
            
            # 2. 构造 Header
            message_headers = {"Content-Type": "application/json; charset=UTF-8"}
            
            # 3. 执行 POST 请求 (使用 json.dumps 确保编码符合要求)
            response = requests.post(
                url=self._google_chat_url,
                headers=message_headers,
                data=json.dumps(app_message),
                timeout=10
            )
            
            # 4. 结果校验
            if response.status_code == 200:
                logger.info(f"[GoogleChat] 消息发送成功")
                return schemas.Response(success=True, message="发送成功")
            else:
                logger.error(f"[GoogleChat] 发送失败，状态码: {response.status_code}, 返回: {response.text}")
                return schemas.Response(success=False, message=f"发送失败: {response.status_code}")
        
        except Exception as e:
            logger.error(f"[GoogleChat] 请求异常: {str(e)}")
            return schemas.Response(success=False, message=f"异常: {str(e)}")

    def test_google_chat(self, **kwargs) -> schemas.Response:
        """测试按钮：模拟发送一条测试内容"""
        if not self._google_chat_url:
            return schemas.Response(success=False, message="请先配置 Webhook URL 并保存")
        
        test_content = "✅ Google Chat 通道配置正确！\n这是一条来自 MoviePilot 的测试消息。"
        return self._do_send(test_content)

    def get_state(self) -> bool:
        return self._enabled

    def get_command(self) -> List[Dict[str, Any]]:
        """定义 UI 界面上的“测试发送”按钮"""
        return [
            {
                "id": "test_google_chat",
                "title": "测试发送",
                "description": "向配置的地址发送测试消息",
                "display": "button",
                "color": "primary"
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """定义外部 Webhook 的接收路径"""
        return [
            {
                "path": "/webhook",
                "endpoint": self.send_notify,
                "methods": ["GET", "POST"],
                "summary": "Google Chat 接收接口",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """定义插件配置界面"""
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 8},
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
            "google_chat_url": ""
        }

    def stop_service(self):
        pass
