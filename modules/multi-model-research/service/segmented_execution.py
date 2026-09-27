"""Durable account-only multi-pass execution with exhaustive source coverage."""
import asyncio
import copy
import json
import uuid
from pathlib import Path

from context_compaction import expand_prompt
from context_preparation import (VERSION, PreparationError, digest, envelope, parse_result,
                                 plan_segments, render_segment, result_instructions, validate_plan)
from packet_markdown import evidence_body
import synthesis_register as registry
import synthesis_parent_transport as parent_transport


def task_prefix(prompt):
    body,_=evidence_body(prompt)
    return prompt[:-len(body)]


def plan_for(engine, run, stage, prompt):
    original=expand_prompt(prompt); body,_=evidence_body(original)
    members=[s for s in run['stages'] if s['round']==stage['round'] and
             s.get('account_profile')==stage.get('account_profile') and s['mode']=='account'] or [stage]
    # All peer instructions are counted, but evidence boundaries are shared exactly.
    from workflow import prompt_for, report_packet
    prefixes=[(s,task_prefix(prompt_for(run,s))) for s in members]
    instructions=result_instructions(['P999999'])
    def fits(value):
        return all(engine.measure_input(prefix+instructions+value, peer)['utilization'] <= .55
                   for peer,prefix in prefixes)
    plan=plan_segments(body,fits)
    if len(plan['parts'])+1>64:
        raise PreparationError('The evidence and final synthesis exceed the multi-pass call limit.')
    packet=report_packet(run,stage)
    plan['protected_register']=packet.get('evidence_register',{})
    plan['source_inventory']=sorted({url for report in packet['reports'] for url in report['citations']})
    pin=envelope(json.dumps({'evidence_register':plan['protected_register'],'source_inventory':plan['source_inventory']},ensure_ascii=False,separators=(',',':')))
    if not all(engine.measure_input(prefix+result_instructions(['P1'],final=True)+pin,peer)['utilization'] < .8 for peer,prefix in prefixes):
        # Every full record is inspected in a separate bounded pass. The parent
        # sees a clearly scoped catalog and those reports, not a silent truncation.
        plan['register_mode']=registry.VERSION
        plan['register_catalog']=registry.catalog(plan['protected_register'])
        plan['register_brief']={k:run.get(k) for k in ('question','scope','language','as_of')}
        claim_ids=[c['id'] for c in plan['protected_register']['claims']]
        def catalog_fits():
            pin=envelope(json.dumps({'evidence_register':registry.parent_register(plan),
                'source_inventory':plan['source_inventory']},ensure_ascii=False,separators=(',',':')))
            return all(engine.measure_input(prefix+result_instructions(['P1'],final=True)+registry.instructions(claim_ids)+pin,peer)['utilization'] < .8
                       for peer,prefix in prefixes)
        if not catalog_fits():
            plan['register_catalog_mode']='lineage-only'
            plan['register_catalog']=registry.catalog(plan['protected_register'],include_statements=False)
            if not catalog_fits():
                raise PreparationError('Even the complete claim lineage exceeds the parent budget; nothing was removed.')
        def register_fits(batch):
            return all(engine.measure_input(prefix+result_instructions([batch['id']])+
                registry.instructions(batch['claim_ids'])+registry.render_batch(batch),peer)['utilization'] <= .65
                for peer,prefix in prefixes)
        plan['register_parts']=registry.plan_batches(plan['protected_register'],plan['register_brief'],register_fits)
        if len(plan['parts'])+len(plan['register_parts'])+1>64:
            raise PreparationError('Evidence, complete claim batches and final synthesis exceed the multi-pass call limit.')
    # Instructions vary slightly with identifiers. Verify the actual final part prompts.
    for part in plan['parts']:
        for peer,prefix in prefixes:
            if not engine.measure_input(prefix+result_instructions([part['id']])+render_segment(part,plan),peer)['fits']:
                raise PreparationError('A measured evidence part no longer fits.')
    return plan


def summary(plan):
    result={'plan_sha256':digest(json.dumps(plan,ensure_ascii=False,sort_keys=True)),
            'version':VERSION,'source_sha256':plan['source_sha256'],'source_bytes':plan['source_bytes'],
            'parts':len(plan['parts']),'coverage_verified':True,'semantic_lossless':False,
            'status':'planned','minimum_calls':len(plan['parts'])+1}
    if plan.get('register_mode'):
        result.update(register_mode=plan['register_mode'],register_parts=len(plan['register_parts']),
                      register_catalog_mode=plan.get('register_catalog_mode','statements'),
                      minimum_calls=len(plan['parts'])+len(plan['register_parts'])+1)
    return result


def saved_plan(engine,run,stage,prompt):
    """Validate the frozen plan on resume, without expensive repartitioning."""
    path=engine.input_path(run,stage).parent/'segmented-journal.json'
    if not path.exists():return None
    state=json.loads(path.read_text())
    if state['input_sha256']!=digest(prompt):
        raise PreparationError('Saved synthesis input changed.')
    plan=state['plan'];body,_=evidence_body(expand_prompt(prompt))
    validate_plan(plan,body);registry.validate_plan(plan)
    if summary(plan)['plan_sha256']!=(stage.get('preparation') or {}).get('plan_sha256'):
        raise PreparationError('Saved synthesis plan changed.')
    return plan


async def execute(engine, run, stage, prompt):
    # Imported lazily to avoid coupling the planner to the application engine.
    from engine import ServiceError
    path=engine.input_path(run,stage).parent/'segmented-journal.json'
    original=expand_prompt(prompt); body,_=evidence_body(original)
    prefix=task_prefix(original)
    if path.exists():
        state=json.loads(await asyncio.to_thread(path.read_text))
        if state['input_sha256']!=digest(prompt):
            raise ServiceError('Segmented input changed.',409,kind='integrity_error')
        plan=state['plan']
    else:
        plan=await asyncio.to_thread(plan_for,engine,run,stage,prompt)
        state={'version':VERSION,'input_sha256':digest(prompt),'plan':plan,'jobs':{}}
    validate_plan(plan,body)
    registry.validate_plan(plan)
    expected=(stage.get('preparation') or {}).get('plan_sha256')
    if expected and summary(plan)['plan_sha256']!=expected:
        raise ServiceError('Saved preparation plan changed.',409,kind='integrity_error')

    async def persist():
        def write():
            temp=path.with_suffix('.tmp'); temp.touch(mode=0o600)
            temp.write_text(json.dumps(state,ensure_ascii=False));temp.replace(path)
        await asyncio.to_thread(write)
    await persist()
    usages=[]
    from workflow import citations
    allowed_urls=set(citations(body))
    from synthesis_boundaries import UnprovidedSourceError, boundary_references, render_references
    boundaries=boundary_references(plan,body,allowed_urls)
    async def validated_report(response,ids,claim_ids=(),key=None):
        report=parse_result(response,ids)
        registry.validate_response(response,claim_ids)
        report,rendering=render_references(report,boundaries,allowed_urls)
        if rendering is not None:
            rendering['raw_response_sha256']=digest(response)
            saved=state.setdefault('boundary_renderings',{})
            if key in saved and saved[key]!=rendering:
                raise PreparationError('The saved source boundary rendering changed.')
            saved[key]=rendering
            await persist()
        return report

    def request_text(data,ids,final=False,claim_ids=()):
        return prefix+result_instructions(ids,final=final)+registry.instructions(claim_ids)+data

    async def raw_call(key, request, ids, regeneration=False):
        budget=await asyncio.to_thread(engine.measure_input,request,stage)
        if not budget['fits']:
            raise ServiceError('Prepared subrequest exceeds the input budget.',409,kind='context_limit')
        job=state['jobs'].get(key)
        if job:
            if job['input_sha256']!=digest(request):
                raise ServiceError('Saved subrequest changed.',409,kind='integrity_error')
            if job['status']=='completed':
                if digest(job['response'])!=job['response_sha256']:
                    raise ServiceError('Saved response changed.',409,kind='integrity_error')
                usages.append(job['usage'])
                return job['response']
            if job['status']=='in_flight':
                if not hasattr(engine.provider,'recover'):
                    raise ServiceError('A previous subrequest may have completed remotely. It was not repeated.',409,kind='submission_uncertain')
                child=dict(stage,request_id=job['request_id'])
                async with engine.lock:
                    latest=await engine.get(run['id']);current=engine.stage(latest,stage['id'])
                    current['request_id']=child['request_id']
                    await engine.store.save(latest)
                try:
                    recover=getattr(engine.provider,'recover_pending',engine.provider.recover)
                    response,usage=await recover(child,request)
                except ServiceError as exc:
                    if exc.settled:
                        job.update(status='rejected',error=str(exc),error_kind=exc.kind,request_settled=True)
                        await persist()
                    raise
                job.update(status='completed',response=response,response_sha256=digest(response),usage=usage)
                await persist();usages.append(usage)
                return response
            if regeneration:
                raise ServiceError('The single artifact regeneration already settled without a valid result; it was not repeated.',
                                   409,kind='integrity_error')
        if len(state['jobs'])>=64 and key not in state['jobs']:
            raise ServiceError('Multi-pass call limit reached; completed parts are saved.',409,kind='context_limit')
        child=copy.deepcopy(stage);child.update(request_id=uuid.uuid4().hex,input_budget=budget)
        async with engine.lock:
            latest=await engine.get(run['id']);current=engine.stage(latest,stage['id'])
            if latest.get('control_state') or latest.get('paused') or current.get('control_state'):
                raise ServiceError('Preparation paused; completed parts are saved.',409,kind='interrupted')
            current['request_id']=child['request_id']
            current['preparation']=dict(summary(plan),status='running',completed_calls=sum(j['status']=='completed' for j in state['jobs'].values()),current=key)
            await engine.store.save(latest)
        if job:state.setdefault('attempt_history',[]).append(dict(job,key=key))
        state['jobs'][key]={'status':'in_flight','request_id':child['request_id'],
                            'input_sha256':digest(request),'input':request,'coverage':ids,'budget':budget}
        await persist()
        try:
            response,usage=await engine.provider.synthesize(child,request)
        except ServiceError as exc:
            if exc.settled or exc.kind in ('quota_wait','login_required','research_unavailable','calibration_required'):
                state['jobs'][key].update(status='rejected',error=str(exc),error_kind=exc.kind,request_settled=exc.settled)
                await persist();raise
            raise ServiceError('Subrequest outcome is uncertain; it was not automatically repeated.',409,kind='submission_uncertain') from exc
        except Exception as exc:
            raise ServiceError('Connection ended without a confirmed outcome; the subrequest was not repeated.',409,kind='submission_uncertain') from exc
        # Save even malformed output before validation: it is evidence for recovery.
        state['jobs'][key].update(status='completed',response=response,response_sha256=digest(response),usage=usage)
        await persist();usages.append(usage)
        return response

    async def regenerate_source_report(key,request,response,ids,claim_ids):
        # This is a new, bounded artifact generation, not URL normalization or
        # acceptance of the invalid report. Frozen evidence and raw output stay intact.
        retry_key=key+'-source-retry-1'
        replacement_request=request+(
            '\n\nSOURCE-VALIDATION RETRY: The previous artifact failed the exact source-address check. '
            'Regenerate the requested report using only the unchanged evidence above. '
            'Copy source URLs exactly as supplied. Do not infer version suffixes, change trailing '
            'slashes, complete partial addresses, or invent links from a title or version label. '
            'If an exact version URL is absent, say that its address was not supplied; retain the '
            'original uncertainty, conditions, conflicting findings and evidence limitations. '
            'Do not remove substantive findings merely to avoid citations. Keep the required JSON '
            'schema and all coverage and claim identifiers. This instruction supplies no new evidence.\n')
        records=state.setdefault('source_regenerations',{})
        record={'kind':'unprovided-source-regeneration-v1','original_job':key,
                'original_response_sha256':digest(response),'original_input_sha256':digest(request),
                'replacement_job':retry_key,'replacement_input_sha256':digest(replacement_request)}
        if key in records:
            if any(records[key].get(k)!=v for k,v in record.items()):
                raise PreparationError('The saved source regeneration provenance changed.')
            record=records[key]
        else:
            recover=getattr(engine.provider,'recover',None)
            if not callable(recover):
                raise PreparationError('Source regeneration requires a confirmed durable receipt.')
            job=state['jobs'][key]
            child=dict(stage,request_id=job['request_id'])
            recovered,_=await recover(child,request)
            if digest(recovered)!=digest(response):
                raise PreparationError('The completed source artifact receipt changed.')
            records[key]=record
            await persist()
        replacement=await raw_call(retry_key,replacement_request,ids,regeneration=True)
        replacement_sha=digest(replacement)
        if record.get('replacement_response_sha256',replacement_sha)!=replacement_sha:
            raise PreparationError('The saved source regeneration response changed.')
        record['replacement_response_sha256']=replacement_sha
        await persist()
        # No recursive regeneration, JSON fallback, source relaxation or refusal retry.
        return await validated_report(replacement,ids,claim_ids,retry_key)

    async def call(key, data, ids, final=False,claim_ids=()):
        from review_execution import retain_recovered_artifact, retained_artifact
        request=request_text(data,ids,final,claim_ids)
        response=await raw_call(key,request,ids)
        job=state['jobs'][key]
        if job.get('artifact_response') is not None:
            response,usage=retained_artifact(job)
            usages[-1]=usage
            return await validated_report(response,ids,claim_ids,key)
        try:
            return await validated_report(response,ids,claim_ids,key)
        except UnprovidedSourceError:
            return await regenerate_source_report(key,request,response,ids,claim_ids)
        except PreparationError as exc:
            if stage.get('provider')!='Claude' or not isinstance(exc.__cause__,json.JSONDecodeError):
                raise
        retry_key=key+'-artifact-retry-1'
        records=state.setdefault('artifact_regenerations',{})
        record={'kind':'invalid-json-regeneration-v1','original_job':key,
                'original_response_sha256':digest(response),'replacement_job':retry_key,
                'same_input_sha256':digest(request)}
        if key in records:
            if any(records[key].get(k)!=v for k,v in record.items()):
                raise PreparationError('The saved artifact regeneration provenance changed.')
            record=records[key]
        else:
            # GET the confirmed receipt before considering a new generation.
            # A missing/uncertain/changed receipt cannot authorize a blind retry.
            if hasattr(engine.provider,'recover'):
                child=dict(stage,request_id=job['request_id'])
                recovered,usage=await engine.provider.recover(child,request)
                if usage.get('artifact_recovery'):
                    report=await validated_report(recovered,ids,claim_ids,key)
                    retain_recovered_artifact(job,recovered,usage)
                    await persist();usages[-1]=usage
                    return report
                if digest(recovered)!=job['response_sha256']:
                    raise PreparationError('The completed artifact receipt changed without recovery provenance.')
            records[key]=record
            await persist()
        replacement=await raw_call(retry_key,request,ids,regeneration=True)
        replacement_sha=digest(replacement)
        if record.get('replacement_response_sha256',replacement_sha)!=replacement_sha:
            raise PreparationError('The saved artifact regeneration response changed.')
        record['replacement_response_sha256']=replacement_sha
        await persist()
        # No recursive recovery or regeneration: an invalid replacement stops.
        return await validated_report(replacement,ids,claim_ids,retry_key)

    try:
        nodes=[]
        for part in plan['parts']:
            result=await call('map-'+part['id'],render_segment(part,plan),[part['id']])
            nodes.append({'ids':[part['id']],'report':result})
        for batch in plan.get('register_parts',[]):
            result=await call('register-'+batch['id'],registry.render_batch(batch),[batch['id']],claim_ids=batch['claim_ids'])
            nodes.append({'ids':[batch['id']],'report':result,'claim_ids':batch['claim_ids']})
        # Preserve previously sent parents. Only unsent work can adopt another
        # reversible transport; the evidence plan and admission margins stay fixed.
        packed_mode = bool(state.get('parent_transport'))
        if not packed_mode and not any(k.startswith('final-') or
                (k.startswith('reduce-') and not k.startswith('reduce-0-')) for k in state['jobs']):
            ids=[i for n in nodes for i in n['ids']]; claims=registry.node_claim_ids(nodes)
            raw=parent_transport.legacy(parent_transport.payload(plan,nodes))
            original_budget=engine.measure_input(request_text(raw,ids,stage['round']==4,claims),stage)
            if original_budget['utilization']>.95:
                packed=parent_transport.packed(parent_transport.payload(plan,nodes))
                packed_mode=engine.measure_input(request_text(packed,ids,stage['round']==4,claims),stage)['utilization'] < original_budget['utilization']
        if packed_mode:
            nodes=await parent_transport.adopt_legacy(state,plan,nodes,call)
            seed={'version':parent_transport.VERSION,'nodes_sha256':digest(registry.encoded(nodes)),
                  'legacy_keys':[k for k in state['jobs'] if k.startswith('reduce-0-') and k[9:].isdigit()]}
            if state.get('parent_transport',seed)!=seed:
                raise PreparationError('Saved parent transport seed changed.')
            state['parent_transport']=seed
            await persist()
        for depth in range(4):
            ids=[ident for n in nodes for ident in n['ids']]
            claim_ids=registry.node_claim_ids(nodes)
            def data(group,partial=False):
                value=parent_transport.payload(plan,group,partial=packed_mode and partial)
                return parent_transport.packed(value) if packed_mode else parent_transport.legacy(value)
            merged=data(nodes)
            if engine.measure_input(request_text(merged,ids,stage['round']==4,claim_ids),stage)['utilization']<=.95:
                if plan.get('register_mode') and set(claim_ids)!={c['id'] for c in plan['protected_register']['claims']}:
                    raise PreparationError('Final synthesis omitted a complete claim-record batch.')
                key=('packed-final-' if packed_mode else 'final-')+str(depth)
                if packed_mode:
                    parent_transport.pin_level(state,depth,nodes,[nodes],[request_text(merged,ids,stage['round']==4,claim_ids)])
                    parent_transport.reserve_calls(state,[key],final=True)
                    await persist()
                result=await call(key,merged,ids,final=stage['round']==4,claim_ids=claim_ids)
                async with engine.lock:
                    latest=await engine.get(run['id']);current=engine.stage(latest,stage['id'])
                    current['preparation']=dict(summary(plan),status='completed',completed_calls=len(state['jobs']))
                    await engine.store.save(latest)
                usage={'segmented':True,'calls':len(usages),'measurements':usages,
                       'coverage':ids,'source_sha256':plan['source_sha256']}
                if packed_mode:
                    usage['parent_transport']=state['parent_transport']
                    usage['parent_transport_levels']=state['parent_transport_levels']
                    result+='\n\n## Parent transport / Birleştirme taşıması\n\nRepeated metadata was encoded reversibly with an in-band dictionary. Each decoded parent payload was checked against its complete original before submission. This proves byte-preserving reconstruction of the structured payload, not model comprehension or factual accuracy. All original reports and request receipts remain saved.\n'
                if state.get('boundary_renderings'):
                    usage['boundary_renderings']=state['boundary_renderings']
                if state.get('artifact_regenerations'):
                    usage['artifact_regenerations']=list(state['artifact_regenerations'].values())
                    result+='\n\n## Provider artifact note / Sağlayıcı çıktı notu\n\nOne or more intermediate artifacts were regenerated once from their exact frozen inputs after invalid provider JSON. This is not reconstruction of lost output or a claim of semantic equivalence. Original and replacement responses remain saved and the same coverage and source checks apply. Geçersiz ara çıktılar aynı özgün girdiden bir kez yeniden üretildi; eski ve yeni yanıtlar korundu.\n'
                if state.get('source_regenerations'):
                    usage['source_regenerations']=list(state['source_regenerations'].values())
                    result+='\n\n## Source-validation recovery / Kaynak doğrulama kurtarması\n\nAn intermediate artifact was regenerated once after introducing an address absent from the frozen evidence. The evidence was unchanged; the replacement received an explicit exact-address instruction and passed the same checks. Both responses remain saved. This is not proof of semantic equivalence or factual accuracy. Kaynak adresi denetiminden geçmeyen ara çıktı bir kez yeniden üretildi; özgün kanıt ve iki yanıt korundu.\n'
                if plan.get('register_mode'):
                    usage.update(register_claim_ids=claim_ids,register_sha256=registry.catalog(plan['protected_register'])['full_register_sha256'])
                    result+='\n\n## Claim-register scope / İddia kaydının kapsamı\n\n'+registry.parent_register(plan)['notice']+'\n\nTam iddia kayıtları ayrı gruplarda incelendi. Özgün kayıtlar ve ara yanıtlar saklanır; son anlatım tüm ham kayıtları tek seferde görmedi. Kapsam kontrolü anlamsal eksiksizlik veya doğruluk garantisi değildir.\n'
                return result,usage
            groups=[];group=[]
            for node in nodes:
                trial=group+[node];covered=[i for n in trial for i in n['ids']]
                if group and engine.measure_input(request_text(data(trial,partial=True),covered,claim_ids=registry.node_claim_ids(trial)),stage)['utilization']>.7:
                    groups.append(group);group=[]
                group.append(node)
            if group:groups.append(group)
            if packed_mode:
                requests=[request_text(data(g,partial=True),[i for n in g for i in n['ids']],claim_ids=registry.node_claim_ids(g)) for g in groups]
                if any(engine.measure_input(text,stage)['utilization']>.7 for text in requests):
                    raise PreparationError('An indivisible parent exceeds reduction headroom; nothing was removed.')
                parent_transport.pin_level(state,depth,nodes,groups,requests)
                parent_transport.reserve_calls(state,[f'packed-reduce-{depth}-{i}' for i in range(len(groups))])
                await persist()
            next_nodes=[]
            for index,group in enumerate(groups):
                ids=[i for n in group for i in n['ids']]
                claim_ids=registry.node_claim_ids(group)
                key=f'packed-reduce-{depth}-{index}' if packed_mode else f'reduce-{depth}-{index}'
                result=await call(key,data(group,partial=True),ids,claim_ids=claim_ids)
                node={'ids':ids,'report':result}
                if claim_ids:node['claim_ids']=claim_ids
                next_nodes.append(node)
            if sum(len(n['report']) for n in next_nodes)>=sum(len(n['report']) for n in nodes):
                raise PreparationError('Intermediate findings did not shrink; no content was truncated.')
            nodes=next_nodes
        raise PreparationError('Bounded multi-pass preparation did not converge.')
    except PreparationError as exc:
        raise ServiceError(str(exc),409,kind='integrity_error') from exc


async def confirm_cancel(engine,run,stage):
    """Called only after the provider confirms stop and the local task has settled."""
    path=engine.input_path(run,stage).parent/'segmented-journal.json'
    if not path.exists():return
    state=json.loads(await asyncio.to_thread(path.read_text))
    changed=False
    for job in state['jobs'].values():
        if job['status']=='in_flight' and job['request_id']==stage.get('request_id'):
            job['status']='cancelled';changed=True
    if changed:
        def write():
            temporary=path.with_suffix('.tmp');temporary.touch(mode=0o600)
            temporary.write_text(json.dumps(state,ensure_ascii=False));temporary.replace(path)
        await asyncio.to_thread(write)
