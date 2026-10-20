"""本课拥有的本地MCP服务：协议stdout，诊断stderr；不访问外部业务系统。"""
import asyncio
import json
from pathlib import Path
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

server = Server('teaching-docs')
SCHEMA = {'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False}
mode, journal = sys.argv[1], Path(sys.argv[2])
def log(kind, **data):
    with journal.open('a',encoding='utf-8') as stream:stream.write(json.dumps({'event':kind,**data},ensure_ascii=False)+'\n')

@server.list_tools()
async def list_tools():
    log('tools/list')
    schema = SCHEMA if mode != 'bad_schema' else {'type':'array'}
    return [types.Tool(name='search.docs',description='查询本地固定运行许可规范；不会运行用户程序。',inputSchema=schema,annotations=types.ToolAnnotations(readOnlyHint=True))]

@server.call_tool()
async def call_tool(name, arguments):
    log('tools/call',name=name,arguments=arguments)
    if mode == 'tool_error':
        return types.CallToolResult(content=[types.TextContent(type='text',text='文档索引暂不可用。')],isError=True)
    if arguments['query']=='slow':await asyncio.sleep(1)
    log('tools/done',name=name)
    return [types.TextContent(type='text',text='运行main.py前需要本次明确许可；旧许可和目录隔离不能替代本次确认。')]

async def main():
    async with stdio_server() as (read,write):
        await server.run(read,write,server.create_initialization_options())
if __name__=='__main__':asyncio.run(main())
