"""
RAGAS评估配置文件
复用现有RAG系统配置
"""
import sys
import os

# 添加父目录到路径，以便导入现有配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 导入现有配置
try:
    import config
except ImportError:
    # 如果导入失败，尝试从父目录导入
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    import config

# RAGAS评估专用配置
RAGAS_CONFIG = {
    "milvus_uri": config.MILVUS_URI,
    "collection_name": config.COLLECTION_NAME,
    "embedding_model": "qwen3-embedding:0.6b",
    "llm_model": "qwen2.5",
    "top_k": 5,
    "reranker_top_n": 3,
    "test_data_path": os.path.join(os.path.dirname(__file__), "test_data.py"),
}

# 从现有配置中获取PDF路径
PDF_BASE_PATH = config.PDF_BASE_PATH
