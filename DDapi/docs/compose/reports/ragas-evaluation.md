---
feature: ragas-evaluation
status: delivered
specs:
  - docs/compose/specs/2026-07-19-ragas-evaluation-design.md
plans:
  - docs/compose/plans/2026-07-19-ragas-evaluation.md
branch: main
commits: dc6653f..5e0dae3
---

# RAGAS评估脚本 — Final Report

## What Was Built

创建了一个RAGAS评估脚本，用于评估现有RAG系统的忠实度(faithfulness)和上下文召回率(context_recall)。脚本位于`scripts/ra/`目录，使用Ollama嵌入模型和LLM，通过Milvus向量数据库进行稠密向量检索，并使用BGE重排序器优化检索结果。

评估脚本成功运行，对3个测试问题进行了评估，结果表明：
- **faithfulness: 1.0000** — 所有生成的答案都基于检索到的上下文
- **context_recall: 0.5000** — 检索到的上下文覆盖了约50%的标准答案

## Architecture

### 组件结构

```
scripts/ra/
├── __init__.py           # 模块初始化
├── config.py             # 配置文件，复用现有RAG系统配置
├── test_data.py          # 测试数据定义
├── ragas_evaluation.py   # 主评估脚本
├── requirements.txt      # 依赖包列表
├── .gitignore            # Git忽略文件
└── README.md             # 使用说明
```

### 数据流

1. **初始化阶段**：加载Milvus向量数据库，创建Ollama嵌入模型和LLM实例
2. **检索阶段**：对每个测试问题，使用稠密向量检索+重排序获取相关文档
3. **生成阶段**：使用LLM基于检索到的上下文生成答案
4. **评估阶段**：使用RAGAS框架评估faithfulness和context_recall

### Design Decisions

- **使用稠密向量检索而非混合检索**：因为Milvus混合检索存在权重配置问题，使用纯稠密向量检索更稳定
- **使用pymilvus直接检索**：langchain-milvus在创建索引时会尝试访问不存在的"vector"字段，改用pymilvus直接操作避免此问题
- **使用ragas 0.2.14**：最新版本与当前langchain-community版本存在兼容性问题

## Usage

### 安装依赖

```bash
pip install -r scripts/ra/requirements.txt
```

### 运行评估

```bash
python scripts/ra/ragas_evaluation.py
```

### 输出示例

```
==================================================
RAGAS评估结果
==================================================
  faithfulness: 1.0000
  context_recall: 0.5000
==================================================
```

## Verification

1. **语法验证**：`python -m py_compile scripts/ra/ragas_evaluation.py` 通过
2. **集成测试**：成功运行完整评估流程，处理3个测试问题
3. **结果验证**：输出包含faithfulness和context_recall分数，无错误信息

## Journey Log

- [dead end] 最初使用langchain-milvus的混合检索，但遇到"weights param mismatch"错误
- [pivot] 改用pymilvus直接进行稠密向量检索，避免langchain-milvus的兼容性问题
- [dead end] ragas 0.4.3导入失败，因为langchain-community缺少vertexai模块
- [pivot] 创建mock vertexai.py文件解决导入问题，后改用ragas 0.2.14
- [lesson] Milvus集合使用自定义字段名(dense/sparse)时，langchain-milvus的自动索引创建会失败

## Source Materials

| File | Role | Notes |
|------|------|-------|
| `docs/compose/specs/2026-07-19-ragas-evaluation-design.md` | 初始设计 | 包含架构和组件设计 |
| `docs/compose/plans/2026-07-19-ragas-evaluation.md` | 实现计划 | 5个任务全部完成 |
| `scripts/ra/ragas_evaluation.py` | 主评估脚本 | 使用pymilvus直接检索 |
| `scripts/ra/config.py` | 配置文件 | 复用现有RAG系统配置 |
| `scripts/ra/test_data.py` | 测试数据 | 基于PDF内容的3个测试问题 |
