"""Bound complete claim records when the synthesis register cannot fit at once.

Original records remain in the frozen plan and are each submitted whole. The
parent receives explicit lineage and a catalog, never a purported lossless
substitute for the full records. Bookkeeping cannot prove semantic completeness.
"""
import copy
import json

from context_preparation import PreparationError, digest, envelope

VERSION = 'bounded-claim-register-v1'
NOTICE = ('The complete claim register was inspected in separate recorded batches. '
          'This catalog preserves original claim identities, source links and input statuses, '
          'but is not the full assessment history. Use the accompanying batch reports for conditions, '
          'exceptions, counter-evidence and unresolved dependencies. Do not treat missing detail as '
          'refutation or promote unverified evidence. All original records remain in the frozen journal. '
          'Exact record coverage is not a guarantee of semantic completeness.')


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def claims(register):
    result = register.get('claims', [])
    ids = [c.get('id') for c in result]
    if not ids or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise PreparationError('The protected register has missing or duplicate claim identities.')
    return result


def catalog(register, include_statements=True):
    records=claims(register)
    urls=list(dict.fromkeys(url for c in records for url in c.get('sources',[])))
    by_url={url:'S'+str(i) for i,url in enumerate(urls,1)}
    result={'scope': VERSION, 'notice': NOTICE, 'full_register_sha256': digest(encoded(register)),
            'source_urls': {ident:url for url,ident in by_url.items()},
            'source_reference_rule': 'Each source_ids item resolves to its exact unchanged URL in source_urls; this is not source verification.',
            'claims': [{'id': c['id'], 'statement': c['statement'],
                        'original_stage': c.get('original_stage'),
                        'source_ids': [by_url[url] for url in c.get('sources',[])],
                        'input_statuses': [{'stage': a.get('stage'), 'status': a.get('status')}
                                           for a in c.get('assessments', [])]} for c in records]}
    if not include_statements:
        # This is explicitly lineage, not a substitute for reading the records.
        # Every unchanged statement is still submitted in a complete R batch.
        for item in result['claims']:item.pop('statement')
        result['scope']='claim-lineage-only'
        result['notice']=('This is only the identity/source/status lineage. Original statements and complete '
            'assessment histories were inspected in the separate complete-record batches; they are not '
            'present in this parent catalog. Reconcile the accompanying batch reports, preserve unresolved '
            'conditions, and never claim to have read all original statements here. '+NOTICE)
    return result


def instructions(ids):
    if not ids:
        return ''
    return ('\nIn addition to coverage and report, return reviewed_claim_ids containing each of these '
            'claim IDs exactly once: ' + encoded(ids) + '. Review the complete supplied records, or the '
            'explicitly identified child lineage for a parent request. Preserve qualifications, conflicting '
            'assessments and uncertainty; do not invent a resolution or claim direct access to omitted records. '
            'Coverage lists are bookkeeping, not proof of factual or semantic correctness.\n')


def record_payload(register, records, brief):
    return {'kind': 'complete_claim_records', 'full_register_sha256': digest(encoded(register)),
            'brief': copy.deepcopy(brief), 'notice': 'These are complete records from a larger register. '
            'Identify dependencies on other claims explicitly; do not infer missing evidence.',
            'records': records}


def plan_batches(register, brief, fits, max_batches=32):
    records = claims(register); result = []; start = 0
    while start < len(records):
        if len(result) >= max_batches:
            raise PreparationError('The complete claim register exceeds the bounded batch count.')
        ident = 'R' + str(len(result) + 1)
        def candidate(end):
            value = copy.deepcopy(records[start:end])
            return {'id': ident, 'claim_ids': [c['id'] for c in value], 'records': value,
                    'payload': record_payload(register, value, brief)}
        low, high, accepted = start + 1, len(records), None
        while low <= high:
            mid = (low + high) // 2; batch = candidate(mid)
            if fits(batch):
                accepted = batch; low = mid + 1
            else:
                high = mid - 1
        if accepted is None or not fits(accepted):
            raise PreparationError('An indivisible claim record exceeds the measured synthesis budget.')
        result.append(accepted); start += len(accepted['records'])
    validate_batches(register, brief, result)
    return result


def validate_batches(register, brief, batches):
    records = claims(register)
    if encoded([c for b in batches for c in b['records']]) != encoded(records):
        raise PreparationError('Complete claim records were omitted, reordered, duplicated or changed.')
    for i, batch in enumerate(batches, 1):
        if (batch['id'] != 'R' + str(i) or not batch['records']
                or batch['claim_ids'] != [c['id'] for c in batch['records']]
                or encoded(batch['payload']) != encoded(record_payload(register, batch['records'], brief))):
            raise PreparationError('A claim record batch or its shared context changed.')


def validate_response(text, ids):
    if not ids:
        return
    from review_contract import read_object
    value = read_object(text)
    found = value.get('reviewed_claim_ids')
    if (not isinstance(found, list) or any(not isinstance(i, str) for i in found)
            or sorted(found) != sorted(ids)):
        raise PreparationError('Intermediate synthesis omitted, duplicated or invented a claim identity.')


def render_batch(batch):
    return envelope(encoded(batch['payload']))


def parent_register(plan):
    if plan.get('register_mode') == VERSION:
        expected = catalog(plan['protected_register'],plan.get('register_catalog_mode')!='lineage-only')
        if plan.get('register_catalog') != expected:
            raise PreparationError('The parent claim catalog changed.')
        return expected
    return plan.get('protected_register', {})


def validate_plan(plan):
    if plan.get('register_mode') is None:
        return
    if plan['register_mode'] != VERSION:
        raise PreparationError('Unknown claim register preparation mode.')
    if plan.get('register_catalog_mode') not in (None,'lineage-only'):
        raise PreparationError('Unknown parent claim catalog mode.')
    parent_register(plan)
    validate_batches(plan['protected_register'], plan['register_brief'], plan['register_parts'])


def node_claim_ids(nodes):
    ids = [i for n in nodes for i in n.get('claim_ids', [])]
    if len(ids) != len(set(ids)):
        raise PreparationError('Claim lineage was duplicated during synthesis.')
    return ids
