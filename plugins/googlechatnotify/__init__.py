import requests
import json
from typing import Any, List, Dict, Tuple, Optional
from app.plugins import _PluginBase
from app.log import logger
from app import schemas

class GoogleChatNotify(_PluginBase):
    # 插件元数据（必须与 manifest.json 和类名严格一致）
    plugin_name = "GoogleChat通知插件"
    plugin_desc = "接收 Webhook 信号并转发至 Google Chat。"
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

    # 私有属性初始化
    _enabled = False
    _google_chat_url = ""

    def init_plugin(self, config: dict = None):
        """初始化配置"""
        if config:
            self._enabled = config.get("enabled", False)
            self._google_chat_url = config.get("google_chat_url", "")

    def get_state(self) -> bool:
        """返回插件是否激活"""
        return self._enabled and bool(self._google_chat_url)

    def send_notify(self, text: str = None, title: str = None, content: str = None, url: str = None) -> schemas.Response:
        """核心通知入口：MoviePilot 系统消息会自动调用此方法"""
        if not self.get_state():
            return schemas.Response(success=False, message="插件未启用")

        # 整理推送内容
        if text:
            msg_text = text
        else:
            msg_text = f"*{title or 'MP通知'}*\n{content or ''}"
            if url:
                msg_text += f"\n\n查看详情: {url}"

        return self._do_send(msg_text)

    def _do_send(self, message: str) -> schemas.Response:
        """底层发送逻辑：参考提供的构造方式"""
        try:
            payload = {"text": message}
            headers = {"Content-Type": "application/json; charset=UTF-8"}
            
            response = requests.post(
                url=self._google_chat_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                return schemas.Response(success=True, message="发送成功")
            else:
                return schemas.Response(success=False, message=f"HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"[GoogleChat] 异常: {str(e)}")
            return schemas.Response(success=False, message=str(e))

    def test_google_chat(self, **kwargs) -> schemas.Response:
        """测试按钮逻辑"""
        return self._do_send("✅ Google Chat 测试通知成功！")

    # --- 必须实现的抽象方法区 ---

    def get_command(self) -> List[Dict[str, Any]]:
        """定义插件按钮"""
        return [
            {
                "id": "test_google_chat",
                "title": "测试发送",
                "description": "发送测试消息到 Google Chat",
                "display": "button",
                "color": "primary"
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        """定义外部 Webhook 接口"""
        return [
            {
                "path": "/webhook",
                "endpoint": self.send_notify,
                "methods": ["GET", "POST"],
                "summary": "Google Chat 转发接口",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """定义设置界面"""
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
                                            'label': 'Webhook URL',
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

    def get_page(self) -> List[dict]:
        """
        核心修复点：明确返回空列表，解决抽象方法实例化报错
        """
        return []

    def stop_service(self):
        """退出插件"""
        pass
