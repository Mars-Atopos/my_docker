"""
测试数据生成模块
基于PDF内容创建测试问题和标准答案
"""
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 导入现有配置
try:
    import config
except ImportError:
    # 如果导入失败，尝试从父目录导入
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
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
