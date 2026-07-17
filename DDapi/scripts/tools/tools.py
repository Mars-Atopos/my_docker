from langchain_core.tools import Tool, StructuredTool
from langchain_community.tools import DuckDuckGoSearchResults
from pydantic import BaseModel, Field
from typing import List, Optional
import config
from SDK import send_robot_private_message

# 导入签到SDK
import sys
import os
taobao_sdk_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SDK', 'taobao-sdk-PYTHON3-auto_1479188381469-20260624')
if taobao_sdk_path not in sys.path:
    sys.path.insert(0, taobao_sdk_path)
import dingtalk.api


# Pydantic输入模型
class SendMessageInput(BaseModel):
    user_id: str = Field(description="用户ID")
    content: str = Field(description="消息内容")

class RememberFactInput(BaseModel):
    user_id: str = Field(description="用户ID")
    fact: str = Field(description="要记住的事实内容")

class RecallMemoryInput(BaseModel):
    user_id: str = Field(description="用户ID")

class CheckinRecordsInput(BaseModel):
    user_ids: List[str] = Field(description="用户ID列表，如: ['user_id1', 'user_id2']")
    start_time: str = Field("", description="开始时间，格式: 2026-07-12 00:00，留空则默认最近一周")
    end_time: str = Field("", description="结束时间，格式: 2026-07-12 23:59，留空则默认当前时间")

class CreateCalendarInput(BaseModel):
    summary: str = Field(description="日程标题")
    start_time: str = Field(description="开始时间，格式: 2026-07-12 09:00")
    end_time: str = Field(description="结束时间，格式: 2026-07-12 18:00")
    description: str = Field("", description="日程描述")
    location: str = Field("", description="地点")

class UpdateCalendarInput(BaseModel):
    event_id: str = Field(description="日程ID")
    summary: str = Field("", description="新标题，留空则不修改")
    start_time: str = Field("", description="新开始时间，留空则不修改")
    end_time: str = Field("", description="新结束时间，留空则不修改")
    description: str = Field("", description="新描述，留空则不修改")
    location: str = Field("", description="新地点，留空则不修改")

class GetCalendarInput(BaseModel):
    event_id: str = Field(description="日程ID")

class DeleteCalendarInput(BaseModel):
    event_id: str = Field(description="日程ID")

class ListCalendarInput(BaseModel):
    start_time: str = Field("", description="开始时间，格式: 2026-07-12 00:00，留空则默认今天")
    end_time: str = Field("", description="结束时间，格式: 2026-07-12 23:59，留空则默认明天")


def get_fresh_token():
    """获取新的access_token并更新到config"""
    class Options:
        client_id = config.client_id
        client_secret = config.client_secret
    token = send_robot_private_message.get_token(Options())
    if token:
        config.accessToken = token
    return token


def create_tools(memory):
    """创建所有工具"""

    #0 搜索工具
    search_tool = DuckDuckGoSearchResults()

    def search_web(query):
        """搜索互联网获取最新信息"""
        try:
            result = search_tool.invoke(query)
            return result if result else "未找到相关信息"
        except Exception as e:
            return f"搜索失败: {str(e)}"

    #1 通过send_robot_private_message发送私聊消息
    def send_private_message_tool(user_id: str, content: str) -> str:
        class Options:
            client_id = config.client_id
            client_secret = config.client_secret
            robot_code = config.robot_code
            msg = content

        token = get_fresh_token()
        if not token:
            return "获取token失败"
        send_robot_private_message.send_robot_private_message(token, Options(), [user_id])
        return "私聊消息发送成功"

    #2 记忆工具
    def remember_fact(user_id: str, fact: str) -> str:
        """记住关于用户的重要信息"""
        memory.add_fact(user_id, fact)
        return f"已记住: {fact}"

    def recall_memory(user_id: str) -> str:
        """查询用户的记忆"""
        return memory.build_context(user_id) or "暂无该用户的记忆"

    #3 签到记录工具
    def get_checkin_records(user_ids: List[str], start_time: str = "", end_time: str = "") -> str:
        """获取用户签到记录"""
        try:
            from datetime import datetime, timedelta

            token = get_fresh_token()
            if not token:
                return "获取签到记录失败: 无法获取access_token"

            now = datetime.now()
            if not start_time:
                start_time = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00")
            if not end_time:
                end_time = now.strftime("%Y-%m-%d %H:%M")

            start_ts = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M").timestamp() * 1000)

            req = dingtalk.api.OapiCheckinRecordGetRequest("https://oapi.dingtalk.com/topapi/checkin/record/get")
            req.userid_list = ",".join(user_ids)
            req.start_time = start_ts
            req.end_time = end_ts
            req.cursor = 0
            req.size = 100

            resp = req.getResponse(token)
            errcode = resp.get("errcode", -1)
            if errcode != 0:
                return f"获取签到记录失败: {resp.get('errmsg', '未知错误')}"

            records = resp.get("result", {}).get("page_list", [])
            if not records:
                return "未找到签到记录"

            output = []
            for r in records:
                userid = r.get("userid", "未知")
                checkin_time = datetime.fromtimestamp(r.get("checkin_time", 0) / 1000).strftime("%Y-%m-%d %H:%M:%S")
                place = r.get("place", "")
                detail_place = r.get("detail_place", "")
                remark = r.get("remark", "")
                output.append(f"- 用户: {userid}\n  时间: {checkin_time}\n  地点: {place} ({detail_place})\n  备注: {remark}")

            return f"找到 {len(records)} 条签到记录:\n" + "\n".join(output)
        except Exception as e:
            return f"获取签到记录失败: {str(e)}"

    #4 日程管理工具（新版API）
    import requests as req_lib

    CALENDAR_URL = f"https://api.dingtalk.com/v1.0/calendar/users/{config.unionid}/calendars/primary/events"

    def _calendar_headers(token):
        return {
            "x-acs-dingtalk-access-token": token,
            "Content-Type": "application/json"
        }

    def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "", location: str = "") -> str:
        """创建钉钉日程"""
        try:
            token = get_fresh_token()
            if not token:
                return "创建日程失败: 无法获取access_token"

            body = {
                "summary": summary,
                "start": {"dateTime": start_time.replace(" ", "T") + ":00+08:00", "timeZone": "Asia/Shanghai"},
                "end": {"dateTime": end_time.replace(" ", "T") + ":00+08:00", "timeZone": "Asia/Shanghai"},
            }
            if description:
                body["description"] = description
            if location:
                body["location"] = {"displayName": location}

            resp = req_lib.post(CALENDAR_URL, json=body, headers=_calendar_headers(token))
            if resp.status_code == 200:
                result = resp.json()
                event_id = result.get("id", "")
                return f"日程创建成功，事件ID: {event_id}"
            else:
                return f"创建日程失败: HTTP {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"创建日程失败: {str(e)}"

    def update_calendar_event(event_id: str, summary: str = "", start_time: str = "", end_time: str = "", description: str = "", location: str = "") -> str:
        """修改钉钉日程"""
        try:
            token = get_fresh_token()
            if not token:
                return "修改日程失败: 无法获取access_token"

            url = f"{CALENDAR_URL}/{event_id}"
            body = {"id": event_id}
            if summary:
                body["summary"] = summary
            if start_time:
                body["start"] = {"dateTime": start_time.replace(" ", "T") + ":00+08:00", "timeZone": "Asia/Shanghai"}
            if end_time:
                body["end"] = {"dateTime": end_time.replace(" ", "T") + ":00+08:00", "timeZone": "Asia/Shanghai"}
            if description:
                body["description"] = description
            if location:
                body["location"] = {"displayName": location}

            resp = req_lib.put(url, json=body, headers=_calendar_headers(token))
            if resp.status_code == 200:
                return "日程修改成功"
            else:
                return f"修改日程失败: HTTP {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"修改日程失败: {str(e)}"

    def get_calendar_event(event_id: str) -> str:
        """查询日程详情"""
        try:
            token = get_fresh_token()
            if not token:
                return "查询日程失败: 无法获取access_token"

            url = f"{CALENDAR_URL}/{event_id}"
            resp = req_lib.get(url, headers=_calendar_headers(token))
            if resp.status_code == 200:
                result = resp.json()
                summary = result.get("summary", "")
                description = result.get("description", "")
                start = result.get("start", {})
                end = result.get("end", {})
                loc = result.get("location", {})
                status = result.get("status", "")

                start_time = start.get("dateTime", start.get("date", ""))
                end_time = end.get("dateTime", end.get("date", ""))
                place = loc.get("displayName", "")

                output = f"日程详情:\n- 标题: {summary}\n- 状态: {status}\n- 开始: {start_time}\n- 结束: {end_time}"
                if description:
                    output += f"\n- 描述: {description}"
                if place:
                    output += f"\n- 地点: {place}"
                return output
            else:
                return f"查询日程失败: HTTP {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"查询日程失败: {str(e)}"

    def delete_calendar_event(event_id: str) -> str:
        """删除日程"""
        try:
            token = get_fresh_token()
            if not token:
                return "删除日程失败: 无法获取access_token"

            url = f"{CALENDAR_URL}/{event_id}"
            resp = req_lib.delete(url, headers=_calendar_headers(token))
            if resp.status_code == 200:
                return "日程删除成功"
            else:
                return f"删除日程失败: HTTP {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"删除日程失败: {str(e)}"

    def list_calendar_events(start_time: str = "", end_time: str = "") -> str:
        """查询日程列表"""
        try:
            from datetime import datetime, timedelta

            token = get_fresh_token()
            if not token:
                return "查询日程列表失败: 无法获取access_token"

            now = datetime.now()
            if not start_time:
                start_time = now.strftime("%Y-%m-%d 00:00")
            if not end_time:
                end_time = (now + timedelta(days=1)).strftime("%Y-%m-%d 23:59")

            start_iso = start_time.replace(" ", "T") + ":00+08:00"
            end_iso = end_time.replace(" ", "T") + ":00+08:00"

            url = f"{CALENDAR_URL}?startTime={start_iso}&endTime={end_iso}"
            resp = req_lib.get(url, headers=_calendar_headers(token))
            if resp.status_code == 200:
                result = resp.json()
                events = result.get("events", [])
                if not events:
                    return "未找到日程"

                output = []
                for e in events:
                    event_id = e.get("id", "")
                    summary = e.get("summary", "")
                    start = e.get("start", {})
                    end = e.get("end", {})
                    start_str = start.get("dateTime", start.get("date", ""))
                    end_str = end.get("dateTime", end.get("date", ""))
                    output.append(f"- ID: {event_id}\n  标题: {summary}\n  时间: {start_str} ~ {end_str}")

                return f"找到 {len(events)} 个日程:\n" + "\n".join(output)
            else:
                return f"查询日程列表失败: HTTP {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"查询日程列表失败: {str(e)}"

    # 工具返回
    return [
        Tool(name="search_web", func=search_web,
             description="搜索互联网获取最新信息，用于新闻、天气、实时事件等需要联网查询的问题"),
        StructuredTool.from_function(
            func=send_private_message_tool,
            name="send_private_message",
            description="发送钉钉私聊消息",
            args_schema=SendMessageInput,
        ),
        StructuredTool.from_function(
            func=remember_fact,
            name="remember_fact",
            description="记住关于用户的重要信息",
            args_schema=RememberFactInput,
        ),
        StructuredTool.from_function(
            func=recall_memory,
            name="recall_memory",
            description="查询用户的记忆",
            args_schema=RecallMemoryInput,
        ),
        StructuredTool.from_function(
            func=get_checkin_records,
            name="get_checkin_records",
            description="获取用户签到记录，查询指定用户在某时间段内的签到详情（不传时间则默认查询最近一周）",
            args_schema=CheckinRecordsInput,
        ),
        StructuredTool.from_function(
            func=create_calendar_event,
            name="create_calendar_event",
            description="创建钉钉日程，返回事件ID",
            args_schema=CreateCalendarInput,
        ),
        StructuredTool.from_function(
            func=update_calendar_event,
            name="update_calendar_event",
            description="修改钉钉日程，根据事件ID修改日程信息",
            args_schema=UpdateCalendarInput,
        ),
        StructuredTool.from_function(
            func=get_calendar_event,
            name="get_calendar_event",
            description="查询钉钉日程详情，根据事件ID获取日程详细信息",
            args_schema=GetCalendarInput,
        ),
        StructuredTool.from_function(
            func=delete_calendar_event,
            name="delete_calendar_event",
            description="删除钉钉日程，根据事件ID删除日程",
            args_schema=DeleteCalendarInput,
        ),
        StructuredTool.from_function(
            func=list_calendar_events,
            name="list_calendar_events",
            description="查询日程列表，获取指定时间段内的所有日程（不传时间则默认查询今天和明天）",
            args_schema=ListCalendarInput,
        ),
    ]
