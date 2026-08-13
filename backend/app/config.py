"""集中式配置：所有外部依赖的 key 均从环境变量读取，未配置时自动降级。"""
import os
from functools import lru_cache


@lru_cache
def get_settings() -> dict:
    return {
        # DeepSeek API（OpenAI 兼容）
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        # 智谱 GLM（OpenAI 兼容）
        "zhipu_api_key": os.getenv("ZHIPU_API_KEY", ""),
        "zhipu_base_url": os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
        "zhipu_model": os.getenv("ZHIPU_MODEL", "glm-4-flash"),
        # 硅基流动 SiliconFlow（OpenAI 兼容）
        "siliconflow_api_key": os.getenv("SILICONFLOW_API_KEY", ""),
        "siliconflow_base_url": os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        "siliconflow_model": os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        # 数据库与向量库
        "database_url": os.getenv("DATABASE_URL", "sqlite:///./recall.db"),
        "chroma_dir": os.getenv("CHROMA_DIR", "./chroma_data"),
        # 存储
        "upload_dir": os.getenv("UPLOAD_DIR", "./uploads"),
    }
