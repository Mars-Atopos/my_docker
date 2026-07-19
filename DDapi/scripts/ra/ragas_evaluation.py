"""
RAGAS评估主脚本
使用RAGAS框架评估RAG系统效果
"""
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 导入配置
from scripts.ra.config import RAGAS_CONFIG

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
    from scripts.ra.test_data import get_test_data
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
