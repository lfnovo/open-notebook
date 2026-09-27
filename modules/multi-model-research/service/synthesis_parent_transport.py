"""Reversible parent encoding without changing frozen evidence or sent requests."""
import json
import copy
import re
from context_preparation import PreparationError, digest, envelope
from reconciliation_text import INSTRUCTIONS as TEXT_INSTRUCTIONS
from synthesis_json_text import encode as transport, restore, INSTRUCTIONS as JSON_INSTRUCTIONS
import synthesis_register as registry

VERSION = 'synthesis-parent-text-tables-v1'


def payload(plan, nodes, partial=False):
    result = {'source_sha256': plan['source_sha256'],
            'notice': 'Intermediate findings from exhaustive source parts; these are not the original full evidence.',
            'evidence_register': registry.parent_register(plan),
            'source_inventory': plan.get('source_inventory', []), 'findings': nodes}
    if partial and plan.get('register_mode'):
        complete=result['evidence_register'];catalog=copy.deepcopy(complete)
        known={c['id'] for c in complete['claims']};ids=set(registry.node_claim_ids(nodes))
        if not ids <= known:raise PreparationError('Partial parent references an unknown claim identity.')
        text='\n'.join(n['report'] for n in nodes)
        ids.update(c for c in known if re.search(r'(?<![\w:])'+re.escape(c)+r'(?![\w:])',text))
        catalog['claims']=[c for c in catalog['claims'] if c['id'] in ids]
        result['evidence_register']=catalog
        result['register_scope']={'kind':'linked_claims_only','complete_catalog_in_final':True,
            'complete_catalog_sha256':digest(registry.encoded(complete)),
            'notice':'This partial reconciliation includes unchanged catalog rows for explicit child claim lineage '
                     'and identities mentioned in these reports. Other complete claim records are processed in '
                     'their own recorded batches and the full catalog is supplied to final reconciliation. '
                     'Do not infer absent evidence, resolve cross-batch conflicts, or claim full-register review here.'}
    return result


def legacy(data):
    return envelope(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def packed(data):
    packet = transport(data)
    # This check is required at admission, not just in the test suite.
    if registry.encoded(restore(packet)) != registry.encoded(data):
        raise PreparationError('Parent transport changed evidence.')
    return TEXT_INSTRUCTIONS + JSON_INSTRUCTIONS + envelope(registry.encoded(packet))


async def adopt_legacy(state, plan, nodes, call):
    """Recover a sent prefix verbatim; never regroup or resubmit its inputs."""
    jobs = state['jobs']
    keys = [k for k in jobs if k.startswith('reduce-0-') and k[9:].isdigit()]
    keys.sort(key=lambda k: int(k[9:]))
    if keys != ['reduce-0-'+str(i) for i in range(len(keys))]:
        raise PreparationError('Legacy reduction prefix has a gap.')
    result = []; position = 0
    for key in keys:
        ids = jobs[key].get('coverage', [])
        group = []; covered = []
        while len(covered) < len(ids) and position < len(nodes):
            node = nodes[position]; group.append(node); covered.extend(node['ids']); position += 1
        if not ids or covered != ids:
            raise PreparationError('Legacy reduction coverage changed.')
        claim_ids = registry.node_claim_ids(group)
        report = await call(key, legacy(payload(plan, group)), ids, claim_ids=claim_ids)
        node = {'ids': ids, 'report': report}
        if claim_ids: node['claim_ids'] = claim_ids
        result.append(node)
    return result + nodes[position:]


def pin_level(state, depth, nodes, groups, requests):
    if (not groups or any(not group for group in groups)
            or [node for group in groups for node in group] != nodes
            or len(groups) != len(requests)):
        raise PreparationError('Parent groups must cover every child exactly once, in order.')
    record = {'version': VERSION, 'nodes_sha256': digest(registry.encoded(nodes)),
              'groups': [[i for n in group for i in n['ids']] for group in groups],
              'requests_sha256': [digest(r) for r in requests]}
    saved = state.setdefault('parent_transport_levels', {})
    key = str(depth)
    if key in saved and saved[key] != record:
        raise PreparationError('Frozen parent transport plan changed.')
    saved[key] = record


def reserve_calls(state, keys, final=False):
    # Preserve the existing whole-stage limit, including invalid completed attempts.
    needed = sum(key not in state['jobs'] for key in keys)
    if len(state['jobs']) + needed + (0 if final else 1) > 64:
        raise PreparationError('Parent reduction exceeds the remaining call budget; completed parts are saved.')
