"""
内容生成器模块
基于原有的RealToolExecutor重构，用于生成和发布小红书内容
"""
import asyncio
import json
import logging
import os
import sys
import tempfile
import shutil
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from pathlib import Path

# 添加原项目路径到sys.path，以便导入原有的模块
parent_dir = Path(__file__).parent.parent.parent / 'xhs'
sys.path.insert(0, str(parent_dir))

try:
    from xhs_llm_client import Configuration, Server, LLMClient, Tool
except ImportError:
    logging.error("无法导入xhs_llm_client模块，请确保原项目目录结构正确")
    raise

logger = logging.getLogger(__name__)


class ContentGenerator:
    """内容生成器 - 负责生成小红书内容并发布"""

    def __init__(self, config: Dict[str, Any]):
        """初始化内容生成器

        Args:
            config: 应用配置字典
        """
        self.config = config
        self.servers = []
        self.llm_client = None
        self.context = None
        self.context_file = None
        self._owns_context_file = False

        # 初始化Configuration
        self.mcp_config = self._create_mcp_config()

    def _create_mcp_config(self) -> Configuration:
        """创建MCP配置对象"""
        # 临时设置环境变量供Configuration使用
        os.environ['LLM_API_KEY'] = self.config.get('llm_api_key', '')
        os.environ['OPENAI_BASE_URL'] = self.config.get('openai_base_url', '')
        os.environ['DEFAULT_MODEL'] = self.config.get('default_model', 'claude-sonnet-4-20250514')

        return Configuration()

    def _prepare_context_file(self, context_file: Optional[str] = None) -> tuple[str, bool]:
        """准备上下文文件"""
        if context_file:
            return context_file, False

        # 使用原项目的模板文件
        script_dir = str(parent_dir)
        template_candidates = [
            os.path.join(script_dir, "agent_context_temple.xml"),
            os.path.join(script_dir, "agent_context.xml"),
        ]

        template_path = None
        for candidate in template_candidates:
            if os.path.exists(candidate):
                template_path = candidate
                break

        if template_path is None:
            raise FileNotFoundError("未找到agent context XML模板文件")

        # 创建临时目录
        temp_dir = tempfile.gettempdir()
        fd, temp_path = tempfile.mkstemp(prefix="agent_context_", suffix=".xml", dir=temp_dir)
        os.close(fd)

        try:
            shutil.copyfile(template_path, temp_path)
        except Exception:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            raise

        return temp_path, True

    def get_research_plan(self, user_topic: str) -> List[Dict[str, Any]]:
        """根据用户主题生成研究计划"""
        return [
            {
                "id": "step1",
                "title": f"针对「{user_topic}」主题信息检索",
                "description": (
                    f"1. 使用网络搜索工具，专门检索与「{user_topic}」相关的最新信息（过去7-30天内）。\n"
                    f"2. 重点搜索关键词：{user_topic}、相关技术名词、主要厂商动态。\n"
                    f"3. 收集权威来源的文章，包括：官方发布、技术博客、新闻报道、研究论文等。\n"
                    f"4. 每条信息必须包含：标题、摘要、发布时间、来源链接、相关的真实图片链接。\n"
                    f"5. 筛选出5-8条最新、最有价值的信息，为深度分析做准备。\n"
                    f"6. 必须检索出与「{user_topic}」相关3-4张图片，并且要保障这个图片是真实存在的网络图片链接（HTTPS地址）"
                ),
                "depends on": []
            },
            {
                "id": "step2",
                "title": f"撰写「{user_topic}」专题文章",
                "description": (
                    f"1. 基于前面的分析，撰写一篇关于「{user_topic}」的专业文章：\n"
                    f"   - 标题可以夸张的手法来描述（≤20字）标题要有吸引力和话题性\n"
                    f"   - 开头吸引眼球，快速切入主题\n"
                    f"   - 正文逻辑清晰：背景→核心技术→应用价值→发展趋势，适当使用emoji表情符号增加趣味性\n"
                    f"   - 结合具体数据、案例和专家观点增强可信度\n"
                    f"   - 语言通俗易懂，避免过于技术化的表述，使用年轻化、亲切的语言风格\n"
                    f"2. 文章长度控制在800-1200字，适合社交媒体阅读。\n"
                    f"3. 准备3-4张高质量配图，必须是真实的网络图片链接（HTTPS地址）。"
                ),
                "depends on": ["step1"]
            },
            {
                "id": "step3",
                "title": "小红书格式适配与内容优化",
                "description": (
                    "1. 将文章调整为适合小红书的格式：\n"
                    "   - 标题控制在20字以内，突出亮点和价值\n"
                    "   - 正文移除所有#开头的标签，改为自然语言表达，正文不超过1000字\n"
                    "   - 提取5个精准的话题标签到tags数组\n"
                    "   - 确保提供3-4张图片，所有链接都是可访问的HTTPS地址\n"
                    "2. 生成标准的JSON格式输出，包含title、content、images、tags四个字段。\n"
                    "3. 验证内容的完整性和格式的正确性，确保符合发布要求。\n"
                    "4. 添加相关内容的url地址放到文后，比如某些github的地址，论文地址等"
                ),
                "depends on": ["step2"]
            },
            {
                "id": "step4",
                "title": "发布到小红书平台",
                "description": (
                    "提取上一步的JSON内容后直接使用<publish_content>工具来进行发布\n"
                    "使用小红书MCP工具，将格式化后的内容进行发布：\n"
                    "   - title作为动态标题\n"
                    "   - content作为正文内容\n"
                    "   - images作为配图（3-4张高质量图片）\n"
                    "   - tags作为话题标签\n"
                    "**注意**: 前面的步骤经过了详细的信息收集了，只需要将内容进行发布即可，不需要这一步做额外的查询工作,如果发布不成功需要修改格式"
                ),
                "depends on": ["step1", "step2", "step3"]
            }
        ]

    async def initialize_servers(self):
        """初始化MCP服务器连接"""
        try:
            # 创建服务器配置
            server_config = {
                "mcpServers": {
                    "jina-mcp-tools": {
                        "args": ["jina-mcp-tools"],
                        "command": "npx",
                        "env": {
                            "JINA_API_KEY": self.config.get('jina_api_key', '')
                        }
                    },
                    "tavily-remote": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "mcp-remote",
                            f"https://mcp.tavily.com/mcp/?tavilyApiKey={self.config.get('tavily_api_key', '')}"
                        ]
                    },
                    "xhs": {
                        "type": "streamable_http",
                        "url": self.config.get('xhs_mcp_url', 'http://localhost:18060/mcp')
                    }
                }
            }

            # 创建服务器实例
            self.servers = [
                Server(name, srv_config)
                for name, srv_config in server_config["mcpServers"].items()
            ]

            # 初始化LLM客户端
            self.llm_client = LLMClient(
                self.config.get('llm_api_key'),
                self.config.get('openai_base_url'),
                self.config.get('default_model', 'claude-sonnet-4-20250514')
            )

            # 初始化所有服务器
            for server in self.servers:
                try:
                    await server.initialize()
                    logger.info(f"成功初始化服务器: {server.name}")
                except Exception as e:
                    logger.error(f"初始化服务器 {server.name} 失败: {e}")

        except Exception as e:
            logger.error(f"初始化服务器失败: {e}")
            raise

    async def get_available_tools(self) -> List[Tool]:
        """获取所有可用的工具"""
        all_tools = []
        for server in self.servers:
            try:
                tools = await server.list_tools()
                all_tools.extend(tools)
                logger.info(f"服务器 {server.name} 提供 {len(tools)} 个工具")
            except Exception as e:
                logger.error(f"从服务器 {server.name} 获取工具失败: {e}")

        return all_tools

    async def execute_step(self, step: Dict[str, Any], available_tools: List[Tool],
                          previous_results: List[Dict[str, Any]], user_topic: str) -> Dict[str, Any]:
        """执行单个步骤

        Args:
            step: 步骤配置
            available_tools: 可用工具列表
            previous_results: 之前步骤的结果
            user_topic: 用户输入的主题

        Returns:
            步骤执行结果
        """
        logger.info(f"执行步骤: {step['id']} - {step['title']}")

        # 将工具转换为OpenAI格式
        openai_tools = [tool.to_openai_tool() for tool in available_tools] if available_tools else None

        system_prompt = f"""你是一个专业的小红书内容创作专家，专门研究「{user_topic}」相关的最新发展。请根据任务背景、之前步骤的执行结果和当前步骤要求选择并调用相应的工具。
        【研究主题】
        核心主题: {user_topic}
        研究目标: 收集、分析并撰写关于「{user_topic}」的专业内容，最终发布到小红书平台
        
        【小红书文案要求】
        🎯 吸引力要素：
        - 使用引人注目的标题，包含热门话题标签和表情符号
        - 开头要有强烈的钩子，激发用户好奇心和共鸣
        - 内容要实用且有价值，让用户有收藏和分享的冲动
        - 语言要轻松活泼，贴近年轻用户的表达习惯
        - 结尾要有互动引导，如提问、征集意见等
        - 适当使用流行梗和网络用语，但保持专业度
        
        【任务背景】
        目标: f'深度研究{user_topic}并生成高质量的社交媒体内容'
        要求: 确保内容专业准确、提供3-4张真实可访问的图片、格式符合小红书发布标准，最好不要有水印，避免侵权的威胁
        
        【当前步骤】
        步骤ID: {step['id']}
        步骤标题: {step['title']}
        """

        # 根据是否有前置结果添加不同的执行指导
        if previous_results:
            system_prompt += "\n【前序步骤执行结果】\n"
            for result in previous_results:
                if result.get('response'):
                    response_preview = result['response'][:1000]  # 限制长度
                    system_prompt += f"▸ {result['step_id']} - {result['step_title']}：\n"
                    system_prompt += f"{response_preview}...\n\n"

            system_prompt += """【执行指南】
                1. 仔细理解前序步骤已获得的信息和资源
                2. 基于已有结果，确定当前步骤需要调用的工具
                3. 充分利用前序步骤的数据，避免重复工作
                4. 如需多个工具协同，可同时调用
                5. 确保当前步骤输出能无缝衔接到下一步骤
                
                ⚠️ 重要提示：
                - 如果前序步骤已提供足够信息，直接整合利用，不要重复检索
                - 如果是内容创作步骤，基于前面的素材直接撰写
                - 如果是发布步骤，直接提取格式化内容进行发布
                """
        else:
            system_prompt += """【执行指南】
            1. 这是一个独立步骤，不依赖其他步骤结果
            2. 分析当前任务需求，选择合适的工具
            3. 为工具调用准备准确的参数
            4. 如需多个工具，可同时调用
            5. 完成所有要求的子任务
            
            ⚠️ 执行要点：
            - 严格按照步骤描述执行
            - 确保工具调用参数准确
            - 收集的信息要完整且相关度高
            """

        user_prompt = step['description']

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            all_tool_call_details = []
            max_iterations = 10
            iteration = 0
            publish_success = False  # 添加发布成功标志

            # 第一轮：初始工具调用
            response = self.llm_client.get_tool_call_response(messages, openai_tools)

            if not response.choices[0].message.tool_calls:
                logger.info("第一轮没有工具调用，直接返回")
                final_content = response.choices[0].message.content or ""
            else:
                # 进入循环处理工具调用
                while iteration < max_iterations:
                    iteration += 1
                    logger.info(f"处理第 {iteration} 轮")

                    message = response.choices[0].message

                    if message.tool_calls:
                        logger.info(f"第 {iteration} 轮发现 {len(message.tool_calls)} 个工具调用")

                        # 添加助手消息
                        assistant_msg = {
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in message.tool_calls
                            ]
                        }
                        messages.append(assistant_msg)

                        # 执行所有工具调用
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.function.name
                            try:
                                arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                            except json.JSONDecodeError:
                                arguments = {}

                            logger.info(f"执行工具: {tool_name} 参数: {arguments}")

                            # 查找对应的服务器并执行工具
                            tool_result = None
                            for server in self.servers:
                                tools = await server.list_tools()
                                if any(tool.name == tool_name for tool in tools):
                                    try:
                                        tool_result = await server.execute_tool(tool_name, arguments)
                                        break
                                    except Exception as e:
                                        logger.error(f"执行工具 {tool_name} 出错: {e}")
                                        tool_result = f"Error: {str(e)}"

                            if tool_result is None:
                                tool_result = f"未找到工具 {tool_name}"

                            # 检测是否是发布工具，并且是否成功
                            if tool_name == "publish_content":
                                # 检查结果是否表明成功
                                result_str = str(tool_result).lower()
                                if "success" in result_str or "成功" in result_str or "published" in result_str:
                                    publish_success = True
                                    logger.info("✅ 检测到发布成功，将在本轮结束后停止迭代")

                            # 记录工具调用详情
                            tool_detail = {
                                "iteration": iteration,
                                "name": tool_name,
                                "arguments": arguments,
                                "result": str(tool_result)
                            }
                            all_tool_call_details.append(tool_detail)

                            # 添加工具结果消息
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(tool_result)
                            })

                    # 如果发布已成功，直接结束迭代
                    if publish_success:
                        logger.info("🎉 发布已成功，停止迭代")
                        # 使用一个简单的最终响应
                        final_content = "内容已成功发布到小红书平台"
                        break

                    # 调用get_final_response决定下一步
                    logger.info("调用get_final_response决定下一步动作...")
                    final_response = self.llm_client.get_final_response(messages, openai_tools)
                    final_message = final_response.choices[0].message

                    if final_message.tool_calls:
                        # 继续下一轮
                        logger.info(f"get_final_response返回了 {len(final_message.tool_calls)} 个工具调用，继续...")
                        response = final_response
                    else:
                        # 任务完成
                        logger.info(f"get_final_response返回最终答案。任务在 {iteration} 轮内完成。")
                        final_content = final_message.content or ""
                        break
                else:
                    # 达到最大迭代次数
                    logger.warning(f"达到最大迭代次数 ({max_iterations})。停止工具调用。")
                    final_content = final_message.content or "任务执行超出最大迭代次数限制"

            # 构建结果
            step_result = {
                "step_id": step['id'],
                "step_title": step['title'],
                "tool_calls": all_tool_call_details,
                "total_iterations": iteration,
                "response": final_content,
                "success": True
            }

            return step_result

        except Exception as e:
            logger.error(f"执行步骤 {step['id']} 出错: {e}")
            return {
                "step_id": step['id'],
                "step_title": step['title'],
                "error": str(e),
                "success": False
            }

    async def generate_and_publish(self, topic: str) -> Dict[str, Any]:
        """生成内容并发布到小红书

        Args:
            topic: 用户输入的主题

        Returns:
            生成和发布结果
        """
        try:
            logger.info(f"开始生成关于「{topic}」的内容...")

            # 获取可用工具
            available_tools = await self.get_available_tools()

            if available_tools is None or len(available_tools) == 0:
                # 初始化服务器
                await self.initialize_servers()
                available_tools = await self.get_available_tools()

            logger.info(f"总共可用工具数: {len(available_tools)}")

            # 获取研究计划
            research_plan = self.get_research_plan(topic)

            # 执行每个步骤
            results = []
            for step in research_plan:
                step_result = await self.execute_step(step, available_tools, results, topic)
                results.append(step_result)

                if not step_result.get('success'):
                    logger.error(f"步骤 {step['id']} 执行失败")
                    return {
                        'success': False,
                        'error': f"步骤 {step['id']} 执行失败: {step_result.get('error', '未知错误')}"
                    }

                logger.info(f"步骤 {step['id']} 执行成功")

            # 从最后一步的结果中提取发布信息
            last_result = results[-1]
            response_content = last_result.get('response', '')

            # 尝试从响应中提取JSON内容（标题、内容、标签等）
            try:
                # 查找step3的结果（小红书格式适配）
                step3_result = next((r for r in results if r['step_id'] == 'step3'), None)
                if step3_result and step3_result.get('response'):
                    # 尝试从响应中提取JSON
                    import re
                    json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', step3_result['response'], re.DOTALL)
                    if json_match:
                        content_data = json.loads(json_match.group())
                    else:
                        content_data = {
                            'title': f'关于{topic}的精彩内容',
                            'content': response_content[:500],
                            'tags': [topic],
                            'images': []
                        }
                else:
                    content_data = {
                        'title': f'关于{topic}的精彩内容',
                        'content': response_content[:500],
                        'tags': [topic],
                        'images': []
                    }
            except Exception as e:
                logger.error(f"解析内容数据失败: {e}")
                content_data = {
                    'title': f'关于{topic}的精彩内容',
                    'content': response_content[:500],
                    'tags': [topic],
                    'images': []
                }

            return {
                'success': True,
                'title': content_data.get('title', ''),
                'content': content_data.get('content', ''),
                'tags': content_data.get('tags', []),
                'images': content_data.get('images', []),
                'publish_status': '已成功发布',
                'full_results': results
            }

        except Exception as e:
            logger.error(f"生成和发布失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

        finally:
            # 清理资源
            await self.cleanup_servers()

    async def cleanup_servers(self):
        """清理服务器连接"""
        for server in reversed(self.servers):
            try:
                await server.cleanup()
            except Exception as e:
                logger.warning(f"清理警告: {e}")
