"""Distinguish an exact frozen URL prefix from an invented source.

Old byte-preserving partitions can cut a URL. Keep those requests and raw
responses unchanged; label the literal prefix as a non-source in derived prose.
"""
import re
from context_preparation import PreparationError, digest, validate_plan


class UnprovidedSourceError(PreparationError):
    """Valid output syntax containing an address absent from frozen evidence."""


def boundary_references(plan, original, allowed):
    validate_plan(plan, original)
    result={};position=0
    for part in plan['parts'][:-1]:
        position+=len(part['text'])
        match=re.search(r'https?://[^\s<>\[\]"`\x00-\x20]*\Z',part['text'])
        if not match:continue
        fragment=match.group()
        if fragment in allowed:continue
        start=position-len(fragment)
        complete=[url for url in allowed if len(url)>len(fragment) and url.startswith(fragment)
                  and original.startswith(url,start)
                  and (start+len(url)==len(original) or original[start+len(url)] in '\\ \t\r\n<>[]"`),;.')]
        if not complete:continue
        # Longest literal match at this exact source position, not URL similarity.
        url=max(complete,key=len)
        result.setdefault(fragment,[]).append({'part_id':part['id'],
            'part_sha256':part['sha256'],'boundary_byte':part['end_byte'],
            'source_sha256':plan['source_sha256'],'complete_url':url})
    return result


def render_references(report, fragments, allowed):
    from workflow import citations
    extra=set(citations(report))-allowed
    if not extra:return report,None
    if extra-set(fragments):
        raise UnprovidedSourceError('Intermediate output introduced a source URL absent from its evidence.')
    rendered=report;references=[]
    for fragment in sorted(extra):
        marker='[split-source-'+digest(fragment)[:16]+']'
        while marker in report:marker=marker[:-1]+'_]'
        # Do not replace prefixes of valid complete URLs or unrelated prose.
        pattern=re.escape(fragment)+r'(?=$|[\s<>\[\]"`),;.!?])'
        rendered,count=re.subn(pattern,lambda match:marker,rendered)
        if not count:raise PreparationError('A split source reference could not be isolated exactly.')
        references.append({'fragment':fragment,'marker':marker,'occurrences':count,
                           'boundary_proofs':fragments[fragment]})
    restored=rendered
    for item in references:restored=restored.replace(item['marker'],item['fragment'])
    if restored!=report:raise PreparationError('Split source rendering failed exact reconstruction.')
    body_bytes=len(rendered.encode())
    notice='\n\n### Frozen input boundary references\n\n'
    for item in references:
        literal=item['fragment'].replace('://','[:]//',1)
        originals=sorted({proof['complete_url'] for proof in item['boundary_proofs']})
        notice+=(item['marker']+' is a literal address prefix cut at a verified input boundary, not a source. '
                 'Displayed with an inert scheme: `'+literal+'`. The complete address occurs at the same '
                 'byte position in the retained original: '+', '.join(originals)+'. '
                 'This mapping does not verify a claim or supply missing source-page text. '
                 'The original response is retained unchanged.\n')
    rendered+=notice
    if set(citations(rendered))-allowed:
        raise PreparationError('Split source rendering introduced an unverified address.')
    return rendered,{'kind':'frozen-url-boundary-rendering-v1','references':references,
        'original_report_sha256':digest(report),'rendered_report_sha256':digest(rendered),
        'body_bytes':body_bytes,'notice':notice,'reconstruction_verified':True}
