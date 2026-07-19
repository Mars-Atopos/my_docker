# RAGAS评估脚本实现计划

> [!NOTE]
> This document may not reflect the current implementation.
> See the final report for up-to-date state:
> [Final Report](../reports/ragas-evaluation.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个简单的RAGAS评估脚本，用于评估现有RAG系统的忠实度和上下文召回率

**Architecture:** 基于现有RAG系统组件，使用RAGAS框架进行评估，采用分层架构确保代码可维护性

**Tech Stack:** Python, LangChain, Milvus, RAGAS, Ollama

## Global Constraints

- 复用现有config.py中的配置
- 使用现有的InfoIndex类进行文档检索
- 使用faithfulness和context_recall评估指标
- 支持PDF内容测试数据生成

---

### Task 1: 创建ra文件夹和基础配置

**Covers:** [S8, S9]

**Files:**
- Create: `scripts/ra/__init__.py`
- Create: `scripts/ra/config.py`
- Create: `scripts/ra/requirements.txt`

**Interfaces:**
- Consumes: 现有config.py中的配置参数
- Produces: ra模块的配置管理

- [ ] **Step 1: 创建ra文件夹结构**

```python
# scripts/ra/__init__.py
"""
RAGAS评估模块
"""
```

- [ ] **Step 2: 创建配置文件**

```python
# scripts/ra/config.py
"""
RAGAS评估配置文件
复用现有RAG系统配置
"""
import sys
import os

# 添加父目录到路径，以便导入现有配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 导入现有配置
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
```

- [ ] **Step 3: 创建依赖文件**

```txt
# scripts/ra/requirements.txt
langchain-classic
langchain-milvus
langchain-ollama
ragas
datasets
pandas
```

- [ ] **Step 4: 验证文件创建**

Run: `ls scripts/ra/`
Expected: 看到创建的三个文件

- [ ] **Step 5: 提交**

```bash
git add scripts/ra/
git commit -m "feat: 创建ra模块基础结构"
```

---

### Task 2: 创建测试数据生成模块

**Covers:** [S4, S5]

**Files:**
- Create: `scripts/ra/test_data.py`

**Interfaces:**
- Consumes: PDF文件路径
- Produces: 测试问题和标准答案数据集

- [ ] **Step 1: 创建测试数据模块**

```python
# scripts/ra/test_data.py
"""
测试数据生成模块
基于PDF内容创建测试问题和标准答案
"""
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 导入现有配置
import config

def get_test_data():
    """
    获取测试数据集
    返回: List[Dict] 包含question和ground_truth的字典列表
    """
    # 基于PDF内容的测试数据
    # 注意：这里需要根据实际PDF内容创建测试数据
    test_data = [
        {
            "question": "习近平文化思想的方法论原则是什么？",
            "ground_truth": "习近平文化思想的方法论原则包括坚持人民至上、坚持自信自立、坚持守正创新、坚持问题导向、坚持系统观念、坚持胸怀天下。"
        },
        {
            "question": "中国哲学社会科学自主知识体系的使命是什么？",
            "ground_truth": "中国哲学社会科学自主知识体系的使命是构建中国特色、中国风格、中国气派的学科体系、学术体系、话语体系。"
        },
        {
            "question": "人类文明新形态视域下中国哲学社会科学面临什么挑战？",
            "ground_truth": "面临如何在全球化背景下保持中国特色、如何回应时代问题、如何实现理论创新等挑战。"
        }
    ]
    
    return test_data

if __name__ == "__main__":
    # 测试数据生成
    data = get_test_data()
    print(f"生成了 {len(data)} 条测试数据")
    for i, item in enumerate(data):
        print(f"{i+1}. {item['question']}")
```

- [ ] **Step 2: 验证测试数据生成**

Run: `python scripts/ra/test_data.py`
Expected: 输出生成了3条测试数据，并显示问题内容

- [ ] **Step 3: 提交**

```bash
git add scripts/ra/test_data.py
git commit -m "feat: 添加测试数据生成模块"
```

---

### Task 3: 创建主评估脚本

**Covers:** [S1, S2, S3, S4, S5, S6]

**Files:**
- Create: `scripts/ra/ragas_evaluation.py`

**Interfaces:**
- Consumes: 配置管理模块, 测试数据模块, 现有RAG组件
- Produces: RAGAS评估结果

- [ ] **Step 1: 创建主评估脚本框架**

```python
# scripts/ra/ragas_evaluation.py
"""
RAGAS评估主脚本
使用RAGAS框架评估RAG系统效果
"""
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 导入配置
from config import RAGAS_CONFIG
import config

# 导入现有RAG组件
from scripts.rag.info_index import InfoIndex

# 导入RAGAS相关库
from ragas import evaluate, RunConfig
from ragas.metrics import faithfulness, context_recall
from datasets import Dataset

def setup_rag_system():
    """
    设置RAG系统
    返回: InfoIndex实例
    """
    try:
        rag_system = InfoIndex()
        print("RAG系统初始化成功")
        return rag_system
    except Exception as e:
        print(f"RAG系统初始化失败: {e}")
        raise

def generate_answer(question, contexts, llm):
    """
    使用LLM生成答案
    """
    context_text = "\n\n".join(contexts)
    prompt = f"""基于以下上下文信息回答问题。如果上下文中没有相关信息，请说"无法从提供的信息中回答"。

上下文信息：
{context_text}

问题：{question}

答案："""
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"答案生成失败: {e}")
        return "无法生成答案"

def run_evaluation():
    """
    执行RAGAS评估
    """
    print("开始RAGAS评估...")
    
    # 1. 设置RAG系统
    rag_system = setup_rag_system()
    
    # 2. 获取测试数据
    from test_data import get_test_data
    test_data = get_test_data()
    
    # 3. 准备评估数据
    evaluation_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }
    
    # 4. 初始化LLM
    from langchain_ollama import ChatOllama
    llm = ChatOllama(model=RAGAS_CONFIG["llm_model"])
    
    # 5. 处理每个测试问题
    for idx, item in enumerate(test_data):
        question = item["question"]
        ground_truth = item["ground_truth"]
        
        print(f"\n处理问题 {idx+1}/{len(test_data)}: {question}")
        
        try:
            # 检索相关文档
            retrieved_docs = rag_system.search(question)
            contexts = [doc.page_content for doc in retrieved_docs]
            print(f"检索到 {len(contexts)} 个文档")
            
            # 生成答案
            answer = generate_answer(question, contexts, llm)
            print(f"答案: {answer[:100]}...")
            
            # 保存到评估数据集
            evaluation_data["question"].append(question)
            evaluation_data["answer"].append(answer)
            evaluation_data["contexts"].append(contexts)
            evaluation_data["ground_truth"].append(ground_truth)
            
        except Exception as e:
            print(f"处理问题 '{question}' 时出错: {e}")
            continue
    
    # 6. 创建RAGAS数据集
    dataset = Dataset.from_dict(evaluation_data)
    
    # 7. 配置RAGAS
    run_config = RunConfig(
        timeout=600,
        max_workers=1,
        max_retries=10,
        max_wait=120
    )
    
    # 8. 执行评估
    print("\n开始RAGAS评估...")
    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(model=RAGAS_CONFIG["embedding_model"])
        
        result = evaluate(
            dataset,
            metrics=[faithfulness, context_recall],
            embeddings=embeddings,
            llm=llm,
            run_config=run_config
        )
        
        # 9. 输出结果
        print("\n" + "="*50)
        print("RAGAS评估结果")
        print("="*50)
        print(f"忠实度 (faithfulness): {result['faithfulness']:.4f}")
        print(f"上下文召回率 (context_recall): {result['context_recall']:.4f}")
        print("="*50)
        
        return result
        
    except Exception as e:
        print(f"RAGAS评估失败: {e}")
        raise

if __name__ == "__main__":
    try:
        result = run_evaluation()
        print("\n评估完成！")
    except Exception as e:
        print(f"\n评估过程中出现错误: {e}")
        sys.exit(1)
```

- [ ] **Step 2: 验证脚本语法**

Run: `python -m py_compile scripts/ra/ragas_evaluation.py`
Expected: 无语法错误

- [ ] **Step 3: 提交**

```bash
git add scripts/ra/ragas_evaluation.py
git commit -m "feat: 添加RAGAS评估主脚本"
```

---

### Task 4: 创建使用说明文档

**Covers:** [S8]

**Files:**
- Create: `scripts/ra/README.md`

**Interfaces:**
- Consumes: 无
- Produces: 使用说明文档

- [ ] **Step 1: 创建README文档**

```markdown
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
```

- [ ] **Step 2: 验证文档创建**

Run: `ls scripts/ra/README.md`
Expected: 文件存在

- [ ] **Step 3: 提交**

```bash
git add scripts/ra/README.md
git commit -m "docs: 添加RAGAS评估使用说明"
```

---

### Task 5: 集成测试和验证

**Covers:** [S7]

**Files:**
- Modify: `scripts/ra/ragas_evaluation.py` (如果需要)

**Interfaces:**
- Consumes: 所有前面任务创建的模块
- Produces: 可运行的评估系统

- [ ] **Step 1: 运行完整评估测试**

Run: `python scripts/ra/ragas_evaluation.py`
Expected: 成功运行并输出评估结果

- [ ] **Step 2: 验证评估结果**

检查输出结果是否包含：
- 忠实度分数
- 上下文召回率分数
- 无错误信息

- [ ] **Step 3: 最终提交**

```bash
git add scripts/ra/
git commit -m "feat: 完成RAGAS评估脚本实现"
```

---

## 依赖关系

```
Task 1 (基础配置)
    ↓
Task 2 (测试数据)
    ↓
Task 3 (主评估脚本)
    ↓
Task 4 (使用说明)
    ↓
Task 5 (集成测试)
```

## 验证标准

1. 所有文件正确创建
2. 脚本无语法错误
3. 能够成功运行评估
4. 输出正确的评估结果
5. 代码符合项目规范