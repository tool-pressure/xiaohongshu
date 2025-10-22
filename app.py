"""
小红书内容自动生成与发布 - Web应用主程序 (FastAPI版本)
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from core.content_generator import ContentGenerator
from config.config_manager import ConfigManager

# 获取当前文件的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    os.makedirs(os.path.join(BASE_DIR, 'config'), exist_ok=True)
    logger.info("应用启动，目录初始化完成")
    yield
    # 关闭时执行
    logger.info("应用关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="小红书内容自动生成与发布系统",
    description="智能生成高质量小红书内容，一键发布",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置模板
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 初始化配置管理器
config_manager = ConfigManager()


# Pydantic 模型
class ConfigRequest(BaseModel):
    api_provider: str = "openai"
    llm_api_key: str
    openai_base_url: str
    default_model: str
    jina_api_key: str = ""
    tavily_api_key: str = ""
    xhs_mcp_url: str = ""


class TestLoginRequest(BaseModel):
    xhs_mcp_url: str


class ValidateModelRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    llm_api_key: str
    openai_base_url: str
    model_name: str


class GeneratePublishRequest(BaseModel):
    topic: str


# 路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    """获取配置信息（隐藏敏感信息）"""
    try:
        config = config_manager.load_config()
        safe_config = {
            'api_provider': config.get('api_provider', 'openai'),
            'llm_api_key': '***' if config.get('llm_api_key') else '',
            'openai_base_url': config.get('openai_base_url', ''),
            'default_model': config.get('default_model', ''),
            'jina_api_key': '***' if config.get('jina_api_key') else '',
            'tavily_api_key': '***' if config.get('tavily_api_key') else '',
            'xhs_mcp_url': config.get('xhs_mcp_url', '')
        }
        return {'success': True, 'config': safe_config}
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def save_config(config_data: ConfigRequest) -> Dict[str, Any]:
    """保存配置"""
    try:
        # 验证必填字段
        if not config_data.llm_api_key or not config_data.openai_base_url or not config_data.default_model:
            raise HTTPException(status_code=400, detail="缺少必填字段")

        # 保存配置
        config_dict = config_data.model_dump()
        config_manager.save_config(config_dict)

        return {'success': True, 'message': '配置保存成功'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate-model")
async def validate_model(request_data: ValidateModelRequest) -> Dict[str, Any]:
    """验证模型是否可用"""
    try:
        # 从配置中获取api_provider
        config = config_manager.load_config()
        api_provider = config.get('api_provider', 'openai')

        llm_api_key = request_data.llm_api_key
        openai_base_url = request_data.openai_base_url
        model_name = request_data.model_name

        if not llm_api_key or not openai_base_url or not model_name:
            raise HTTPException(status_code=400, detail="请检查LLM API key、Base URL和模型名称是否填写完整")

        # 尝试调用模型进行验证
        try:
            from core.llm_adapter import create_llm_adapter

            # 创建适配器
            adapter = create_llm_adapter(
                api_provider=api_provider,
                api_key=llm_api_key,
                base_url=openai_base_url,
                model=model_name
            )

            # 发送一个简单的测试请求
            response = adapter.chat_completion(
                messages=[
                    {"role": "user", "content": "Hi"}
                ],
                temperature=0.5,
                max_tokens=50
            )

            # 检查响应类型
            if isinstance(response, str):
                # 检查是否是HTML响应
                if response.strip().startswith('<'):
                    raise HTTPException(
                        status_code=500,
                        detail=f'API返回了HTML页面而不是JSON响应,请检查Base URL是否正确。常见问题:\n1. Base URL应该以/v1结尾\n2. 确认API服务地址正确\n3. 检查是否需要额外的认证配置'
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f'API返回了非预期的字符串响应: {response[:200]}'
                )

            if response and hasattr(response, 'choices') and response.choices:
                return {
                    'success': True,
                    'message': f'模型 {model_name} 验证成功',
                    'model': model_name,
                    'provider': api_provider
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f'模型 {model_name} 响应异常: 没有返回有效的choices'
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"模型验证异常: {error_msg}", exc_info=True)

            # 检查常见错误类型
            if 'model_not_found' in error_msg.lower() or 'does not exist' in error_msg.lower() or 'invalid model' in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail=f'模型 {model_name} 不存在或不可用'
                )
            elif 'authentication' in error_msg.lower() or 'unauthorized' in error_msg.lower() or '401' in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail='API Key无效或未授权,请检查密钥是否正确'
                )
            elif 'Invalid URL' in error_msg or 'Connection' in error_msg:
                raise HTTPException(
                    status_code=500,
                    detail=f'无法连接到API服务,请检查Base URL是否正确: {error_msg}'
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f'模型验证失败: {error_msg}'
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-login")
async def test_login(request_data: TestLoginRequest) -> Dict[str, Any]:
    """测试小红书账号登录"""
    try:
        xhs_mcp_url = request_data.xhs_mcp_url

        if not xhs_mcp_url:
            raise HTTPException(status_code=400, detail="请提供小红书MCP服务地址")

        # 调用小红书MCP服务测试连接
        try:
            response = requests.get(f"{xhs_mcp_url}/health", timeout=5)
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': '小红书MCP服务连接成功',
                    'status': 'connected'
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f'服务响应异常: {response.status_code}'
                )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail=f'无法连接到MCP服务: {str(e)}'
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-and-publish")
async def generate_and_publish(request_data: GeneratePublishRequest) -> Dict[str, Any]:
    """生成内容并发布到小红书"""
    try:
        topic = request_data.topic

        if not topic:
            raise HTTPException(status_code=400, detail="请输入主题")

        # 检查配置是否完整
        config = config_manager.load_config()
        if not config.get('llm_api_key') or not config.get('xhs_mcp_url'):
            raise HTTPException(status_code=400, detail="请先完成配置")

        # 创建内容生成器
        generator = ContentGenerator(config)

        # 异步执行内容生成和发布
        result = await generator.generate_and_publish(topic)

        if result.get('success'):
            return {
                'success': True,
                'message': '内容生成并发布成功',
                'data': {
                    'title': result.get('title', ''),
                    'content': result.get('content', ''),
                    'tags': result.get('tags', []),
                    'images': result.get('images', []),
                    'publish_status': result.get('publish_status', ''),
                    'publish_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', '生成失败')
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成和发布失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """获取任务状态（用于后续扩展异步任务）"""
    return {
        'success': True,
        'task_id': task_id,
        'status': 'completed',
        'progress': 100
    }


# 挂载静态文件 - 必须在所有路由定义之后
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )