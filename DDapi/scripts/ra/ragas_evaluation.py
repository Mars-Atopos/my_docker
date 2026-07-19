"""
RAGAS评估主脚本
使用RAGAS框架评估RAG系统效果
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.documents import Document
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_core.retrievers import BaseRetriever
from ragas import evaluate, RunConfig
from ragas.metrics import faithfulness, context_recall
from datasets import Dataset
from pymilvus import connections, Collection
from pydantic import Field

from scripts.ra.config import RAGAS_CONFIG
from scripts.ra.test_data import get_test_data


class MilvusDenseRetriever(BaseRetriever):
    """使用pymilvus直接进行稠密向量检索"""
    collection_name: str = Field()
    embedding_model: OllamaEmbeddings = Field()
    top_k: int = Field(default=5)

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str):
        connections.connect(host="localhost", port="19530")
        col = Collection(self.collection_name)
        col.load()

        # 生成查询向量
        query_embedding = self.embedding_model.embed_query(query)

        # 搜索
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = col.search(
            data=[query_embedding],
            anns_field="dense",
            param=search_params,
            limit=self.top_k,
            output_fields=["text"]
        )

        docs = []
        for hits in results:
            for hit in hits:
                text = hit.entity.get("text", "")
                docs.append(Document(page_content=text, metadata={"score": hit.score}))

        return docs


def setup_rag_system():
    """设置RAG系统（使用稠密向量检索 + BGE重排序）"""
    try:
        embedding_model = OllamaEmbeddings(model=RAGAS_CONFIG["embedding_model"])

        # 使用自定义检索器
        retriever = MilvusDenseRetriever(
            collection_name=RAGAS_CONFIG["collection_name"],
            embedding_model=embedding_model,
            top_k=RAGAS_CONFIG["top_k"]
        )

        # BGE重排序器
        model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-large")
        compressor = CrossEncoderReranker(model=model, top_n=RAGAS_CONFIG["reranker_top_n"])

        # 重排序检索器
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=retriever
        )

        print("RAG系统初始化成功")
        return compression_retriever
    except Exception as e:
        print(f"RAG系统初始化失败: {e}")
        raise


def generate_answer(question, contexts, llm):
    """使用LLM生成答案"""
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
    """执行RAGAS评估"""
    print("开始RAGAS评估...")

    # 1. 设置RAG系统
    retriever = setup_rag_system()

    # 2. 获取测试数据
    test_data = get_test_data()

    # 3. 准备评估数据
    evaluation_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    # 4. 初始化LLM
    llm = ChatOllama(model=RAGAS_CONFIG["llm_model"])

    # 5. 处理每个测试问题
    for idx, item in enumerate(test_data):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"\n处理问题 {idx+1}/{len(test_data)}: {question}")

        try:
            # 检索相关文档
            retrieved_docs = retriever.invoke(question)
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

    if not evaluation_data["question"]:
        print("没有成功处理的问题，无法进行评估")
        return None

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

        # ragas 0.2.x 返回的是 Dataset 格式
        if hasattr(result, 'to_pandas'):
            df = result.to_pandas()
            print(df.to_string())
            print("\n平均分数:")
            for col in df.columns:
                if col not in ['question', 'answer', 'contexts', 'ground_truth']:
                    try:
                        print(f"  {col}: {df[col].mean():.4f}")
                    except Exception:
                        print(f"  {col}: {df[col].tolist()}")
        else:
            for key, value in result.items():
                if isinstance(value, list):
                    print(f"{key}: {value}")
                else:
                    print(f"{key}: {value:.4f}")

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
