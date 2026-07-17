'''
redis 记忆功能
职责：用户画像（facts + summary）+ 会话管理 + 上下文组装
对话历史由 LangChain SimpleRedisChatMessageHistory 统一管理
'''
import json
import redis
import config
from datetime import datetime

class MemoryStore:
    """
    Redis 数据结构：
      mem:{uid}:facts       — 用户事实/长期记忆（List）
      mem:{uid}:summary     — 用户画像摘要（String，90天过期）
      mem:{uid}:session_num — 当前会话编号（String，自增）
    """
    def __init__(self) -> None:
        self.rc = redis.Redis.from_url(config.redis_url, decode_responses=True)
        self.max_facts = 30       # 最大事实条数
        self.max_summary_len = 1000  # 最大摘要长度

    def _key(self, uid, tag):
        return f"mem:{uid}:{tag}"

    # ---- 会话管理 ----
    def get_session_id(self, uid):
        """获取当前会话 ID（user_id:session_num）"""
        num = self.rc.get(self._key(uid, "session_num")) or "0"
        return f"{uid}:{num}"

    def reset_session(self, uid):
        """重置会话：递增 session_num，清除该用户的 LangChain 对话历史"""
        # 递增会话编号
        new_num = self.rc.incr(self._key(uid, "session_num"))
        # 清除旧会话的 LangChain 对话历史（保留 facts 和 summary）
        old_session_id = f"{uid}:{new_num - 1}"
        self.rc.delete(f"lc:{old_session_id}:history")
        return f"{uid}:{new_num}"

    # ---- 用户画像 + 长期记忆 ----
    def add_fact(self, uid, fact):
        """记一条事实（喜好、习惯、特征等）"""
        key = self._key(uid, "facts")
        entry = json.dumps({
            'fact': fact,
            't': datetime.now().strftime("%Y-%m-%d")
        }, ensure_ascii=False)
        self.rc.rpush(key, entry)
        self.rc.ltrim(key, -self.max_facts, -1)

    def get_facts(self, uid):
        """取所有事实，返回事实字符串列表"""
        raw = self.rc.lrange(self._key(uid, "facts"), 0, -1)
        return [json.loads(r)["fact"] for r in raw]

    # ---- 压缩摘要 ----
    def set_summary(self, uid, text):
        """保存/更新摘要"""
        self.rc.set(self._key(uid, "summary"), text, ex=86400 * 90)

    def get_summary(self, uid):
        return self.rc.get(self._key(uid, "summary")) or ""

    # ---- 组装完整上下文 ----
    def build_context(self, uid, recent_history=""):
        """
        组装注入 system prompt 的完整上下文
        recent_history: 由外部（agent.py）从 LangChain 传入的最近对话文本
        """
        parts = []

        # 用户画像摘要
        summary = self.get_summary(uid)
        if summary:
            parts.append(f"【用户画像】\n{summary}")

        # 已知事实
        facts = self.get_facts(uid)
        if facts:
            parts.append("【已知信息】\n" + "\n".join(f"- {f}" for f in facts))

        # 最近对话（从外部传入）
        if recent_history:
            parts.append(f"【最近对话】\n{recent_history}")

        return "\n\n".join(parts) if parts else "（暂无该用户的历史信息）"
