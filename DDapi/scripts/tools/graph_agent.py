'''
langgraph 图智能体
'''
from typing import TypedDict, Annotated, Any
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.redis import RedisSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import config
from tools.tools import create_tools
from tools.memory_store import MemoryStore

#初始化
memory=MemoryStore()
tools=create_tools(memory)
llm=config.llm
llm_with_tools=llm.bind_tools(tools)

# Redis Checkpointer
checkpointer_cm = RedisSaver.from_conn_string(config.redis_url)
checkpointer = checkpointer_cm.__enter__()
checkpointer.setup()

# 定义状态
class AgentState(TypedDict):
    messages:Annotated[list[Any],add_messages]
    user_id:str
    memory_content:str

#------------------------节点------------------------
def agent_node(state:AgentState):
    '''agent节点：LLM决策是否调用工具'''
    system_msg= SystemMessage(content=config.system_text)

    #如果有记忆上下文，注入到对话开头
    if state.get('memory_content'):
        context_msg=HumanMessage(content=f'[上下文]\n{state["memory_content"]}')
        messages=[system_msg,context_msg]+state['messages']
    else:
        messages=[system_msg]+state['messages']

    response=llm_with_tools.invoke(messages)
    return {'messages':[response]}


def save_memory_node(state:AgentState):
    '''保存本轮对话到记忆系统'''
    user_id=state['user_id']
    messages=state['messages']

    user_msg=None
    ai_msg=None
    for msg in reversed(messages):
        if isinstance(msg,AIMessage) and ai_msg is None:
            ai_msg=msg
        elif isinstance(msg,HumanMessage) and user_msg is None:
            user_msg=msg
        
        if user_msg and ai_msg:
            break
    
    if user_msg and ai_msg:
        memory.save_turn(user_id,user_msg.content,ai_msg.content)
    return {}
        
#------------------------条件边------------------------
def is_tool_call(state:AgentState):
    '''判断是否调用工具,不调用的话就保存记忆'''
    last_msg=state['messages'][-1]
    if hasattr(last_msg,'tool_calls') and last_msg.tool_calls:
        return 'tools'
    return 'save_memory'

#------------------------构建图------------------------
def build_graph():
    workflow=StateGraph(AgentState)

    # 定义节点
    workflow.add_node('agent_node',agent_node)
    workflow.add_node('save_memory_node',save_memory_node)
    workflow.add_node('tools_node',ToolNode(tools))

    workflow.add_edge(START,'agent_node')
    workflow.add_conditional_edges(
        'agent_node',
        is_tool_call,
        {
            'tools':'tools_node',
            'save_memory':'save_memory_node'
        }
    )
    workflow.add_edge('tools_node','agent_node')
    workflow.add_edge('save_memory_node',END)

    return workflow.compile(checkpointer=checkpointer)


#------------------------对外接口------------------------
graph=build_graph()

def chat(user_id:str,message:str):
    '''处理一轮对话'''
    memory_context=memory.build_context(user_id)

    result=graph.invoke(
        {
            'messages':[HumanMessage(content=message)],
            'user_id':user_id,
            'memory_content':memory_context
        },
        config={'configurable':{'thread_id':user_id}}
    )

    for msg in reversed(result['messages']):
        if isinstance(msg,AIMessage):
            return msg.content
        
    return "抱歉，处理消息时出现错误"



    


