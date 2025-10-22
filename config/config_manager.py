"""
配置管理模块
负责读取、保存和管理应用配置
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir='config'):
        """初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        # 使用绝对路径，确保无论从哪里运行都能找到配置目录
        if not os.path.isabs(config_dir):
            # 获取项目根目录（app.py所在目录）
            project_root = Path(__file__).parent.parent
            self.config_dir = project_root / config_dir
        else:
            self.config_dir = Path(config_dir)

        self.config_dir.mkdir(exist_ok=True)

        self.config_file = self.config_dir / 'app_config.json'
        self.servers_config_file = self.config_dir / 'servers_config.json'
        self.env_file = self.config_dir / '.env'

    def load_config(self) -> Dict[str, Any]:
        """加载应用配置

        Returns:
            配置字典
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                return {}
        return {}

    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存应用配置

        Args:
            config: 配置字典

        Returns:
            是否保存成功
        """
        try:
            # 保存到JSON配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 同时保存到.env文件
            self._save_to_env(config)

            # 更新servers_config.json
            self._update_servers_config(config)

            logger.info("配置保存成功")
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def _save_to_env(self, config: Dict[str, Any]):
        """保存配置到.env文件

        Args:
            config: 配置字典
        """
        env_content = f"""# LLM API Configuration
            LLM_API_KEY={config.get('llm_api_key', '')}
            OPENAI_BASE_URL={config.get('openai_base_url', '')}
            
            # Default Model Configuration
            DEFAULT_MODEL={config.get('default_model', 'claude-sonnet-4-20250514')}
            
            # Jina API Configuration
            JINA_API_KEY={config.get('jina_api_key', '')}
            
            # Tavily API Configuration
            TAVILY_API_KEY={config.get('tavily_api_key', '')}
            
            # XHS MCP Service Configuration
            XHS_MCP_URL={config.get('xhs_mcp_url', '')}
            """
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)

    def _update_servers_config(self, config: Dict[str, Any]):
        """更新MCP服务器配置文件

        Args:
            config: 配置字典
        """
        servers_config = {
            "mcpServers": {
                "jina-mcp-tools": {
                    "args": ["jina-mcp-tools"],
                    "command": "npx",
                    "env": {
                        "JINA_API_KEY": config.get('jina_api_key', '')
                    }
                },
                "tavily-remote": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "mcp-remote",
                        f"https://mcp.tavily.com/mcp/?tavilyApiKey={config.get('tavily_api_key', '')}"
                    ]
                },
                "xhs": {
                    "type": "streamable_http",
                    "url": config.get('xhs_mcp_url', 'http://localhost:18060/mcp')
                }
            }
        }

        with open(self.servers_config_file, 'w', encoding='utf-8') as f:
            json.dump(servers_config, f, indent=2, ensure_ascii=False)

    def get_servers_config_path(self) -> str:
        """获取服务器配置文件路径

        Returns:
            配置文件绝对路径
        """
        return str(self.servers_config_file.absolute())

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """验证配置的完整性

        Args:
            config: 配置字典

        Returns:
            (是否有效, 错误信息)
        """
        required_fields = {
            'llm_api_key': 'LLM API Key',
            'openai_base_url': 'API Base URL',
            'default_model': '默认模型',
            'xhs_mcp_url': '小红书MCP服务地址'
        }

        for field, name in required_fields.items():
            if not config.get(field):
                return False, f"缺少必填字段: {name}"

        # 验证URL格式
        import re
        url_pattern = r'^https?://'

        if not re.match(url_pattern, config.get('openai_base_url', '')):
            return False, "API Base URL格式不正确"

        if not re.match(url_pattern, config.get('xhs_mcp_url', '')):
            return False, "小红书MCP服务地址格式不正确"

        return True, ""
