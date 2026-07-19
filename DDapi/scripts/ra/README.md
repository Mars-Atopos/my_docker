# RAGAS评估脚本

## 简介
本脚本用于评估RAG（检索增强生成）系统的效果，使用RAGAS框架进行忠实度和上下文召回率评估。

## 文件说明
- `ragas_evaluation.py`: 主评估脚本
- `test_data.py`: 测试数据生成模块
- `config.py`: 配置文件
- `requirements.txt`: 依赖包列表

## 使用方法

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行评估
```bash
python scripts/ra/ragas_evaluation.py
```

### 3. 查看结果
评估结果将显示：
- 忠实度 (faithfulness): 评估答案是否基于检索到的上下文
- 上下文召回率 (context_recall): 评估检索到的上下文是否包含标准答案的关键信息

## 配置说明
配置文件 `config.py` 包含以下参数：
- `milvus_uri`: Milvus连接地址
- `collection_name`: 集合名称
- `embedding_model`: 嵌入模型
- `llm_model`: LLM模型
- `top_k`: 检索文档数量
- `reranker_top_n`: 重排序后保留的文档数量

## 测试数据
测试数据基于PDF文件内容生成，可以在 `test_data.py` 中修改或添加测试问题。

## 注意事项
1. 确保Milvus服务正在运行
2. 确保Ollama服务正在运行
3. 确保PDF文件已正确索引
4. 评估过程可能需要较长时间，取决于测试数据数量
