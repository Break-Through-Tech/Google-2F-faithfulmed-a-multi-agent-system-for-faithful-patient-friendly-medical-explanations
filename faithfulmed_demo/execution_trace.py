"""Per-session execution records. No prompts, credentials or provider exceptions."""
import asyncio
import copy
import inspect
import json
import time
from datetime import datetime, timezone
from google.adk.events import Event, EventActions

def preview(value):
    if hasattr(value,'model_dump'):value=value.model_dump()
    if value is None or isinstance(value,(str,int,float,bool,list,dict)):
        encoded=json.dumps(value,ensure_ascii=False,default=lambda _: '[unavailable]')
        return value if len(encoded)<=12000 else {'preview':encoded[:12000],'truncated':True}
    return '[unavailable]'

def event(ctx):
    return Event(invocation_id=ctx.invocation_id,author='WorkflowTrace',
        actions=EventActions(state_delta={'execution_trace':copy.deepcopy(ctx.session.state.get('execution_trace',[]))}))

def start(ctx,stage,name,kind,inputs=None):
    rows=list(ctx.session.state.get('execution_trace',[]))
    row=dict(id=f'T{len(rows)+1}',stage=stage,name=name,kind=kind,status='running',
        started_utc=datetime.now(timezone.utc).isoformat(),duration_ms=None,inputs=preview(inputs))
    rows.append(row);ctx.session.state['execution_trace']=rows
    return row['id'],time.perf_counter()

def finish(ctx,token,status='completed',output=None,error=None):
    identifier,started=token
    rows=copy.deepcopy(ctx.session.state['execution_trace'])
    row=next(r for r in rows if r['id']==identifier)
    row.update(status=status,duration_ms=round((time.perf_counter()-started)*1000,2),output=preview(output))
    if error:
        row['error_type']=type(error).__name__
        code=getattr(error,'code',None)
        if isinstance(code,int):row['service_code']=code
    ctx.session.state['execution_trace']=rows
    return event(ctx)

def skip(ctx,stage,name,kind,reason):
    token=start(ctx,stage,name,kind)
    return finish(ctx,token,'skipped',{'reason':reason})

def fail_open_calls(ctx,stage,error):
    rows=copy.deepcopy(ctx.session.state.get('execution_trace',[]))
    now=datetime.now(timezone.utc)
    for row in rows:
        if row['stage']==stage and row['kind']!='stage' and row['status']=='running':
            row.update(status='failed',error_type=type(error).__name__,
                duration_ms=round((now-datetime.fromisoformat(row['started_utc'])).total_seconds()*1000,2))
    ctx.session.state['execution_trace']=rows

async def call(ctx,stage,name,kind,fn,box,*args,inputs=None,**kwargs):
    token=start(ctx,stage,name,kind,inputs)
    yield event(ctx)
    try:
        result=await fn(*args,**kwargs) if inspect.iscoroutinefunction(fn) else await asyncio.to_thread(fn,*args,**kwargs)
    except Exception as exc:
        yield finish(ctx,token,'failed',error=exc)
        raise
    box['result']=result
    yield finish(ctx,token,output=result)

def interrupt(state):
    rows=copy.deepcopy(state.get('execution_trace',[]))
    now=datetime.now(timezone.utc)
    for r in rows:
        if r['status']=='running':
            r['status']='interrupted'
            r['duration_ms']=round((now-datetime.fromisoformat(r['started_utc'])).total_seconds()*1000,2)
    state['execution_trace']=rows
