import json
import subprocess
import threading
import time
import unittest
from unittest.mock import patch
import server


class BridgeTests(unittest.TestCase):
    def test_calibration_fingerprint_changes_with_cli_version_model_and_instructions(self):
        with patch.object(server,'_cli_version',return_value='test-cli-1'), patch.object(server.Path,'stat') as stat:
            stat.return_value.st_mtime_ns=1;stat.return_value.st_size=100
            original=server.runtime_fingerprint('claude-account')
            self.assertEqual(len(original),64)
            with patch.dict(server.MODELS['claude-account'],research_cli_model='different-model'):
                self.assertNotEqual(server.runtime_fingerprint('claude-account'),original)
            with patch.object(server,'SYSTEM','changed-system'):
                self.assertNotEqual(server.runtime_fingerprint('claude-account'),original)
            with patch.object(server,'_cli_version',return_value='test-cli-2'):
                self.assertNotEqual(server.runtime_fingerprint('claude-account'),original)

    def test_context_observations_are_distinct_from_aggregate_claude_usage(self):
        from unittest.mock import Mock
        raw={'input_tokens':30,'cache_read_input_tokens':300,'cache_creation_input_tokens':3000,'output_tokens':20,
             'iterations':[{'type':'message','input_tokens':10,'cache_read_input_tokens':100,'cache_creation_input_tokens':1000},
                           {'type':'message','input_tokens':20,'cache_read_input_tokens':200,'cache_creation_input_tokens':2000}]}
        proc=Mock(returncode=0);proc.communicate.return_value=(json.dumps({'result':'complete','usage':raw,
            'num_turns':2,'subtype':'success','stop_reason':'end_turn','is_error':False}),'')
        with patch.object(server.subprocess,'Popen',return_value=proc):
            _,usage=server.run_cli('claude-account','input','research_synthesis')
        self.assertEqual(usage['prompt_tokens'],3330)
        self.assertEqual(usage['first_context_tokens'],1110)
        self.assertEqual(usage['max_context_tokens'],2220)
        self.assertEqual(usage['context_observations'],2)
        self.assertTrue(usage['context_observations_complete'])

    def test_continuation_contexts_come_from_unique_stream_messages(self):
        from unittest.mock import Mock
        first={'input_tokens':2,'cache_creation_input_tokens':115854,'cache_read_input_tokens':0}
        second={'input_tokens':4,'cache_creation_input_tokens':64065,'cache_read_input_tokens':115854}
        events=[]
        for ident,raw in [('first',first),('second',second)]:
            for kind in ('thinking','text'):
                events.append({'type':'assistant','session_id':'session','parent_tool_use_id':None,
                               'message':{'id':ident,'usage':raw,'content':[{'type':kind}]}})
        events.append({'type':'result','session_id':'session','result':'complete','num_turns':2,
                       'subtype':'success','stop_reason':'end_turn','is_error':False,
                       'usage':{'input_tokens':6,'cache_creation_input_tokens':179919,
                                'cache_read_input_tokens':115854,'output_tokens':81261,
                                'iterations':[dict(second,type='message')]}})
        proc=Mock(returncode=0);proc.communicate.return_value=('\n'.join(map(json.dumps,events)),'')
        with patch.object(server.subprocess,'Popen',return_value=proc):
            text,usage=server.run_cli('claude-account','input','research_synthesis')
        self.assertEqual(text,'complete')
        self.assertEqual(usage['prompt_tokens'],295779)
        self.assertEqual(usage['first_context_tokens'],115856)
        self.assertEqual(usage['max_context_tokens'],179923)
        self.assertEqual(usage['context_observations'],2)
        self.assertEqual(usage['cli_num_turns'],2)
        self.assertEqual(usage['context_observation_source'],'assistant-messages')
        self.assertTrue(usage['context_observations_complete'])

    def test_partial_terminal_iterations_cannot_attest_first_context(self):
        from unittest.mock import Mock
        data={'result':'complete','num_turns':2,'subtype':'success','stop_reason':'end_turn','is_error':False,
              'usage':{'input_tokens':3000,'iterations':[{'type':'message','input_tokens':2000}]}}
        proc=Mock(returncode=0);proc.communicate.return_value=(json.dumps(data),'')
        with patch.object(server.subprocess,'Popen',return_value=proc):
            text,usage=server.run_cli('claude-account','input','research_synthesis')
        self.assertEqual(text,'complete')
        self.assertFalse(usage['context_observations_complete'])
        self.assertNotIn('first_context_tokens',usage)

    def test_markdown_research_transport_is_verbatim_and_restricted(self):
        body=self.request(local_profile='research_synthesis',local_prompt_format='research-markdown-v1')
        body['messages']=[{'role':'system','content':'System instructions'}, {'role':'user','content':'İğüş\r\n```json\n{"a":"\\n"}\n```\t'}]
        text,fn,fmt=server.prepare_prompt(body)
        self.assertEqual(text,'System instructions\n\n'+body['messages'][1]['content'])
        self.assertIsNone(fn);self.assertEqual(fmt,{})
        for patch in ({'local_profile':'default'}, {'tools':[{'type':'function','function':{'name':'x'}}]}, {'response_format':{'type':'json_object'}}, {'messages':[body['messages'][1]]}):
            with self.assertRaises(server.BridgeError):server.prepare_prompt(body|patch)
        with self.assertRaises(server.BridgeError):server.prepare_prompt(body|{'local_prompt_format':'unknown'})

    def test_research_records_requested_model_and_effort_without_attesting_resolved_model(self):
        with patch.object(server,'run_cli',return_value=('Report',{'total_tokens':10})):
            result=server.completion(self.request(local_profile='research_synthesis'))
        self.assertEqual(result['execution']['requested_model'],'claude-fable-5-1')
        self.assertEqual(result['execution']['requested_effort'],'max')
        self.assertIn('not independently attested',result['execution']['model_selection'])

    def request(self, **extra):
        return dict(model='claude-account', messages=[{'role': 'user', 'content': 'Merhaba'}], **extra)

    def test_multimodal_input_is_rejected_instead_of_silently_lost(self):
        body = self.request()
        body['messages'][0]['content'] = [{'type': 'image_url', 'image_url': {'url': 'http://example.com/x.png'}}]
        with self.assertRaises(server.BridgeError):
            server.prepare_prompt(body)

    def test_unrecognized_model_cannot_become_a_cli_argument(self):
        body = self.request()
        body['model'] = '--dangerously-skip-permissions'
        with self.assertRaises(server.BridgeError):
            server.prepare_prompt(body)

    def test_request_failure_releases_account_lock(self):
        with patch.object(server, 'run_cli', side_effect=server.BridgeError('test', 502)):
            with self.assertRaises(server.BridgeError):
                server.completion(self.request())
        self.assertEqual(server.QUEUES['claude-account'].status(), {'active': 0, 'waiting': 0})

    def test_concurrent_requests_wait_and_run_in_fifo_order(self):
        queue = server.AccountQueue(capacity=4, wait_seconds=4)
        order = []
        def work(number):
            with queue.slot():
                order.append(number)
        with queue.slot():
            threads = []
            for i in range(3):
                t = threading.Thread(target=work, args=(i,)); t.start(); threads.append(t)
                deadline = time.monotonic() + 1
                while queue.status()['waiting'] != i + 1 and time.monotonic() < deadline:
                    time.sleep(0.005)
            time.sleep(2.05)  # Reproduce the previous 2-second rejection boundary.
            self.assertEqual(order, [])
        for t in threads: t.join(2)
        self.assertEqual(order, [0, 1, 2])
        self.assertEqual(queue.status(), {'active': 0, 'waiting': 0})

    def test_timeout_removes_waiter_without_blocking_next_request(self):
        queue = server.AccountQueue(wait_seconds=0.03)
        with queue.slot():
            with self.assertRaises(server.BridgeError) as error:
                with queue.slot(): pass
            self.assertEqual(error.exception.status, 504)
        with queue.slot(): pass
        self.assertEqual(queue.status(), {'active': 0, 'waiting': 0})

    def test_queue_capacity_is_bounded(self):
        queue = server.AccountQueue(capacity=0)
        with self.assertRaises(server.BridgeError) as error:
            with queue.slot(): pass
        self.assertEqual(error.exception.status, 429)

    def test_structured_function_result_is_openai_compatible(self):
        tool = {'type': 'function', 'function': {'name': 'summary', 'parameters': {'type': 'object'}}}
        with patch.object(server, 'run_cli', return_value=('```json\n{"summary":"ok"}\n```', {})):
            data = server.completion(self.request(tools=[tool]))
        choice = data['choices'][0]
        self.assertEqual(choice['finish_reason'], 'tool_calls')
        call = choice['message']['tool_calls'][0]
        self.assertEqual(call['function']['name'], 'summary')
        self.assertEqual(json.loads(call['function']['arguments']), {'summary': 'ok'})

    def test_invalid_json_is_not_presented_as_success(self):
        with patch.object(server, 'run_cli', return_value=('not JSON', {})):
            with self.assertRaises(server.BridgeError):
                server.completion(self.request(response_format={'type': 'json_object'}))

    def test_provider_api_keys_and_parent_agent_variables_are_not_inherited(self):
        with patch.dict(server.os.environ, {'OPENAI_API_KEY': 'secret', 'ANTHROPIC_API_KEY': 'secret', 'GEMINI_API_KEY': 'secret', 'CLAUDECODE': '1'}):
            env = server.cli_env('claude')
        for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'CLAUDECODE'):
            self.assertNotIn(key, env)

    def test_provider_refusal_is_not_misreported_as_missing_login(self):
        from unittest.mock import Mock
        process = Mock(returncode=1)
        process.communicate.return_value = (json.dumps({'is_error': True,
            'stop_reason': 'refusal', 'result': 'Provider declined this request.'}), '')
        with patch.object(server.subprocess, 'Popen', return_value=process):
            with self.assertRaises(server.BridgeError) as error:
                server.run_cli('claude-account', 'test')
        self.assertEqual(error.exception.status, 403)
        self.assertIn('declined', str(error.exception))

    def test_gemini_missing_text_profile_cannot_fall_back_to_general_agent(self):
        with patch.object(server.JOBS, 'spawn') as spawn:
            probe = spawn.return_value
            probe.communicate.return_value = ('other-agent\n', '')
            probe.returncode = 0
            probe.args = ['agy', 'agents']
            with self.assertRaises(server.BridgeError) as error:
                server.run_cli('gemini-account', 'test')
        self.assertEqual(error.exception.status, 503)
        self.assertEqual(spawn.call_count, 1)  # profile inspection only, no research

    def test_gemini_terminal_quota_with_exit_zero_blocks_future_calls(self):
        from unittest.mock import Mock
        policy=server.ModelPolicy({'gemini':'test'})
        probe=Mock(returncode=0,args=['test','agents']);probe.communicate.return_value=('notebook-preliminary\n','')
        result={'event':'result','result':{'status':'ERROR','response':'','error':
            'API error (attempt 3): RESOURCE_EXHAUSTED (code 429): Individual quota reached. Resets in 95h0m0s.'}}
        proc=Mock(returncode=0);proc.communicate.return_value=(json.dumps(result),'')
        with patch.object(server,'MODEL_POLICY',policy),patch.object(server.JOBS,'spawn',side_effect=[probe,proc]) as spawn:
            with self.assertRaises(server.BridgeError) as error:server.run_cli('gemini-account','input','preliminary_research')
            self.assertEqual(error.exception.status,429)
            self.assertGreater(error.exception.retry_at,time.time()+94*3600)
            self.assertIn('retry_at',error.exception.payload()['error'])
            with self.assertRaises(server.BridgeError):server.run_cli('gemini-account','input','preliminary_research')
            self.assertEqual(spawn.call_count,2)

    def test_gemini_report_keywords_do_not_mask_actual_terminal_failure(self):
        from unittest.mock import Mock
        probe=Mock(returncode=0,args=['test','agents']);probe.communicate.return_value=('notebook-preliminary\n','')
        events=[{'event':'assistant','message':'Research topics: quota, login, credentials, 429'},
                {'event':'result','result':{'status':'ERROR','response':'Partial report',
                                           'error':'Connection reset by peer'}}]
        proc=Mock(returncode=0);proc.communicate.return_value=('\n'.join(map(json.dumps,events)),'')
        with patch.object(server,'MODEL_POLICY',server.ModelPolicy({'gemini':'test'})),patch.object(server.JOBS,'spawn',side_effect=[probe,proc]):
            with self.assertRaises(server.BridgeError) as error:server.run_cli('gemini-account','input','preliminary_research')
        self.assertEqual(error.exception.status,502)
        self.assertNotIn('Partial report',str(error.exception))

    def test_research_profile_raises_effort_without_enabling_tools(self):
        normal = server.command_for('chatgpt-account')
        research = server.command_for('chatgpt-account', 'research_synthesis')
        self.assertIn('model_reasoning_effort="low"', normal)
        self.assertIn('model_reasoning_effort="max"', research)
        self.assertEqual(research[research.index('--model')+1], 'gpt-6-astra')
        self.assertNotIn('--model', normal)
        self.assertIn('web_search="disabled"', research)
        claude = server.command_for('claude-account', 'research_synthesis')
        self.assertEqual(claude[claude.index('--effort')+1], 'max')
        self.assertEqual(claude[claude.index('--model')+1], 'claude-fable-5-1')
        self.assertEqual(claude[claude.index('--tools')+1], '')
        with self.assertRaises(server.BridgeError):
            server.prepare_prompt(self.request(local_profile='arbitrary-command'))
        with patch.object(server,'run_cli',return_value=('Test synthesis',{})) as run:
            server.completion(self.request(local_profile='research_synthesis'))
            self.assertEqual(run.call_args.args[2], 'research_synthesis')

    def test_partial_provider_outputs_are_not_accepted(self):
        from unittest.mock import Mock
        examples = [
            ('claude-account', json.dumps({'result':'Partial answer','stop_reason':'max_tokens','usage':{}})),
            ('chatgpt-account', '\n'.join(json.dumps(x) for x in [
                {'type':'item.completed','item':{'type':'agent_message','text':'Partial answer'}},
                {'type':'turn.failed','error':{'message':'interrupted'}}])),
        ]
        for model, stdout in examples:
            process = Mock(returncode=0)
            process.communicate.return_value = (stdout, '')
            with patch.object(server.subprocess,'Popen',return_value=process):
                with self.assertRaises(server.BridgeError) as error:
                    server.run_cli(model,'test','research_synthesis')
                self.assertIn('partial output',str(error.exception))

    def test_codex_progress_is_not_included_in_the_final_report(self):
        from unittest.mock import Mock
        events=[{'type':'item.completed','item':{'type':'agent_message','text':text}}
                for text in ('I will compare the evidence.','I found a disagreement.','Final evidence-based report.')]
        events.append({'type':'turn.completed','usage':{'input_tokens':100,'output_tokens':20}})
        process=Mock(returncode=0)
        process.communicate.return_value=('\n'.join(json.dumps(e) for e in events),'')
        with patch.object(server.subprocess,'Popen',return_value=process):
            text,usage=server.run_cli('chatgpt-account','test','research_synthesis')
        self.assertEqual(text,'Final evidence-based report.')
        self.assertEqual(usage['total_tokens'],120)

if __name__ == '__main__':
    unittest.main()
