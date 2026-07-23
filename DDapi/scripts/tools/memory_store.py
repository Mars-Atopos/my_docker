'''
Redis 记忆模块
职责：对话历史管理 + 用户画像自动总结
使用 MessagesPlaceholder 注入历史对话
'''
import json
import redis
import config
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# 配置参数
HISTORY_WINDOW = 20        # 保留最近 20 轮对话
SUMMARY_TRIGGER = 10       # 每 10 轮触发一次画像总结
MAX_SUMMARY_LEN = 500      # 画像摘要最大长度


class MemoryStore:
    """
    Redis 数据结构：
      mem:{uid}:history     — 最近对话消息（List，JSON 序列化）
      mem:{uid}:summary     — 用户画像摘要（String，90天过期）
      mem:{uid}:turn_count  — 累计对话轮数（String，自增）
    """
    def __init__(self) -> None:
        self.rc = redis.Redis.from_url(config.redis_url, decode_responses=True)

    def _key(self, uid, tag):
        return f"mem:{uid}:{tag}"

    # ---- 会话管理 ----
    def get_session_id(self, uid):
        """获取当前会话 ID（兼容旧接口）"""
        return uid

    def reset_session(self, uid):
        """重置会话：清空对话历史和轮数计数（保留画像）"""
        self.rc.delete(self._key(uid, "history"))
        self.rc.delete(self._key(uid, "turn_count"))

    # ---- 对话历史（MessagesPlaceholder 兼容格式）----
    def save_turn(self, uid, user_msg, ai_msg):
        """保存一轮对话（HumanMessage + AIMessage）"""
        key = self._key(uid, "history")
        entries = [
            json.dumps({"type": "human", "content": user_msg}, ensure_ascii=False),
            json.dumps({"type": "ai", "content": ai_msg}, ensure_ascii=False),
        ]
        for entry in entries:
            self.rc.rpush(key, entry)
        # 只保留最近 HISTORY_WINDOW 轮（每轮 2 条消息）
        self.rc.ltrim(key, -(HISTORY_WINDOW * 2), -1)

    def get_history_messages(self, uid):
        """获取历史对话，返回 LangChain Message 列表（供 MessagesPlaceholder 使用）"""
        key = self._key(uid, "history")
        raw = self.rc.lrange(key, 0, -1)
        messages = []
        for item in raw:
            d = json.loads(item)
            if d["type"] == "human":
                messages.append(HumanMessage(content=d["content"]))
            elif d["type"] == "ai":
                messages.append(AIMessage(content=d["content"]))
        return messages

    def get_all_history_text(self, uid):
        """获取所有历史对话的纯文本（供画像总结使用）"""
        key = self._key(uid, "history")
        raw = self.rc.lrange(key, 0, -1)
        lines = []
        for item in raw:
            d = json.loads(item)
            role = "用户" if d["type"] == "human" else "小白"
            lines.append(f"{role}: {d['content']}")
        return "\n".join(lines)

    # ---- 轮数计数 ----
    def increment_turn(self, uid):
        """轮数 +1，返回当前轮数"""
        return self.rc.incr(self._key(uid, "turn_count"))

    def get_turn_count(self, uid):
        """获取当前轮数"""
        return int(self.rc.get(self._key(uid, "turn_count")) or 0)

    def reset_turn_count(self, uid):
        """重置轮数计数"""
        self.rc.delete(self._key(uid, "turn_count"))

    # ---- 用户画像 ----
    def set_summary(self, uid, text):
        """保存/更新用户画像"""
        self.rc.set(self._key(uid, "summary"), text, ex=86400 * 90)

    def get_summary(self, uid):
        """获取用户画像"""
        return self.rc.get(self._key(uid, "summary")) or ""

    def should_summarize(self, uid):
        """判断是否需要触发画像总结"""
        return self.get_turn_count(uid) >= SUMMARY_TRIGGER

    def build_summary_prompt(self, uid, current_summary=""):
        """构建画像总结的 prompt，交给 LLM 执行"""
        history_text = self.get_all_history_text(uid)
        if not history_text:
            return None

        if current_summary:
            return f"""你是一个用户画像分析助手。请根据以下信息更新用户画像。

【现有画像】
{current_summary}

【最近对话记录】
{history_text}

请用一段简洁的文字概括这个用户的特征（性格、喜好、职业、沟通风格等），不超过{MAX_SUMMARY_LEN}字。
只输出画像内容，不要加任何前缀或解释。"""
        else:
            return f"""你是一个用户画像分析助手。请根据以下对话记录，生成用户画像。

【对话记录】
{history_text}

请用一段简洁的文字概括这个用户的特征（性格、喜好、职业、沟通风格等），不超过{MAX_SUMMARY_LEN}字。
只输出画像内容，不要加任何前缀或解释。"""

    def compact_history_after_summary(self, uid):
        """画像总结后，只保留最近 3 轮对话"""
        key = self._key(uid, "history")
        self.rc.ltrim(key, -6, -1)  # 3 轮 = 6 条消息
