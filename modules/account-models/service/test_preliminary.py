import json
import server
from preliminary import trace

def test_profiles_keep_synthesis_isolated():
    for name,model,effort in [('chatgpt-account','gpt-6-astra','ultra'),('claude-account','claude-fable-5-1','max'),('gemini-account','gemini-3.1-pro-high','high')]:
        cmd=server.command_for(name,'preliminary_research')
        assert model in cmd and (effort in cmd or any(effort in x for x in cmd))
    old=server.command_for('chatgpt-account','research_synthesis')
    assert 'web_search="disabled"' in old
    web=server.command_for('chatgpt-account','preliminary_research')
    assert 'web_search="live"' in web and web[web.index('code_mode_host')-1]=='--enable'
    claude=server.command_for('claude-account','preliminary_research')
    assert claude[claude.index('--tools')+1]=='WebSearch,WebFetch'

def test_tool_evidence_requires_search_and_read_not_final_claims():
    claim=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'I searched and read'}})
    assert not trace(claim,'codex')[0]['searched']
    events=[{'type':'item.completed','item':{'type':'web_search','action':{'type':'search'}}},{'type':'item.completed','item':{'type':'web_search','action':{'type':'other'},'query':'https://example.org/'}}]
    result=trace('\n'.join(map(json.dumps,events)),'codex')[0]
    assert result['searched'] and result['read_sources']
    event={'event':'step_update','step_update':{'state':'DONE','tool_name':'run_command','tool_info':{'parameters':{}}}}
    assert trace(json.dumps(event),'gemini')[0]['unexpected_tools']==['run_command']


def test_review_profiles_keep_tools_out_of_reconciliation():
    for name in ('chatgpt-account','claude-account'):
        web=server.command_for(name,'research_review')
        merge=server.command_for(name,'review_merge')
        if name.startswith('chatgpt'):
            assert 'web_search="live"' in web and 'web_search="disabled"' in merge
            assert 'exec' in web and '--ignore-user-config' in web
        else:
            assert web[web.index('--tools')+1]=='WebSearch,WebFetch'
            assert merge[merge.index('--tools')+1]==''
            assert merge[merge.index('--output-format')+1]=='stream-json'
            assert '--verbose' in merge and '--restricted' in merge
            assert '--strict-mcp-config' in web and '--no-chrome' in web


def test_failed_claude_tool_invocations_do_not_count_as_research():
    events=[{'type':'assistant','message':{'content':[{'type':'tool_use','id':'a','name':'WebFetch'}]}},
            {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'a','is_error':True}]}}]
    assert not trace('\n'.join(map(json.dumps,events)),'claude')[0]['read_sources']
    events[-1]['message']['content'][0]['is_error']=False
    assert trace('\n'.join(map(json.dumps,events)),'claude')[0]['read_sources']
    assert trace(json.dumps({'type':'item.completed','item':{'type':'command_execution'}}),'codex')[0]['unexpected_tools']
