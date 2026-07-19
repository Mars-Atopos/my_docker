# RAGAS评估脚本设计

> [!NOTE]
> This document may not reflect the current implementation.
> See the final report for up-to-date state:
> [Final Report](../reports/ragas-evaluation.md)

## [S1] 问题
需要为现有的RAG系统创建一个评估脚本，使用RAGAS框架来评估检索增强生成的效果。现有系统使用Milvus向量数据库、BM25+稠密向量混合检索、BGE重排序器，需要评估其忠实度和上下文召回率。

## [S2] 解决方案概述
创建一个简单的RAGAS评估脚本，基于用户提供的示例代码，但修改为使用现有RAG系统的配置。脚本将：
1. 连接到现有的Milvus向量数据库
2. 使用现有的嵌入模型和LLM
3. 创建测试数据集（基于PDF内容）
4. 执行RAGAS评估并输出结果

## [S3] 架构
脚本将采用以下架构：
- 配置层：从config.py导入现有配置
- 检索层：使用现有的InfoIndex类进行文档检索
- 生成层：使用现有的LLM生成答案
- 评估层：使用RAGAS框架进行评估

## [S4] 组件
1. **配置管理**：复用现有config.py中的配置
2. **检索器**：使用现有的InfoIndex类，支持混合检索和重排序
3. **测试数据生成**：基于PDF内容创建测试问题和标准答案
4. **RAGAS评估器**：配置faithfulness和context_recall指标
5. **结果输出**：格式化输出评估结果

## [S5] 数据流
1. 加载配置和现有RAG组件
2. 创建测试数据集（问题、标准答案）
3. 对于每个测试问题：
   - 检索相关文档
   - 生成答案
   - 收集上下文
4. 构建RAGAS评估数据集
5. 执行评估并输出结果

## [S6] 错误处理
- 网络连接错误：捕获Milvus连接异常
- 模型加载错误：捕获嵌入模型或LLM加载异常
- 检索错误：捕获检索过程中的异常
- 评估错误：捕获RAGAS评估过程中的异常

## [S7] 测试
1. 单元测试：测试各个组件的功能
2. 集成测试：测试整个评估流程
3. 验证测试：使用已知数据验证评估结果的正确性

## [S8] 文件结构
```
scripts/ra/
├── ragas_evaluation.py      # 主评估脚本
├── test_data.py            # 测试数据定义
├── config.py               # 配置文件（复用现有配置）
└── README.md               # 使用说明
```

## [S9] 依赖
- langchain-classic
- langchain-milvus
- langchain-ollama
- ragas
- datasets
- pandas（用于结果展示）

## [S10] 配置参数
- MILVUS_URI: Milvus连接地址（默认localhost:19530）
- COLLECTION_NAME: 集合名称（默认dingding_info）
- EMBEDDING_MODEL: 嵌入模型（默认qwen3-embedding:0.6b）
- LLM_MODEL: LLM模型（默认qwen2.5）
- TOP_K: 检索文档数量（默认5）
- RERANKER_TOP_N: 重排序后保留的文档数量（默认3）