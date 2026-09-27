"""Append-only evidence accounting. Structural checks are not fact verification.

Original reports are never edited. An omitted claim remains in the register and
an invalid rejection never replaces an earlier assessment. Parallel assessments
remain separate; provider order and majority never decide truth.
"""
from __future__ import annotations
import hashlib
import json
import re
from urllib.parse import urlsplit
from packet_markdown import ledger_blocks

VERSION = 2
STATUSES = {'supported', 'disputed', 'rejected', 'unverified'}

PROTOCOL = '''Kanıt koruma ve eleştiri protokolü (v2):
- Önceki raporlar değiştirilemez referanstır; yeni yorumun onları değiştirmez. Aynı iddianın kimliğini, kaynaklarını, kapsamını, tarihini ve önceki itirazlarını koru. Bir sağlayıcının adını otorite veya ret gerekçesi sayma.
- Önemli karar iddialarını kaydet. İlk kez ortaya koyduğun her iddiaya CURRENT_STAGE:C001 gibi benzersiz kimlik ver. Paketteki evidence_register.claims içindeki HER kimlik için değerlendirme yaz; benzer iddiaları ilişkilendir ama kimlikleri silme veya anlamlarını değiştirme.
- Bir eleştiriyi kabul etmeden önce hedef iddiayı doğru kapsam ve tarih ile yeniden ifade et; eleştirinin gerçekten onu çürütüp çürütmediğini, kaynakların aynı ölçüyü/dönemi karşılaştırıp karşılaştırmadığını incele. Eleştirene de aynı kanıt standardını uygula. Yanıt verememek veya erişememek yanlışlık kanıtı değildir.
- supported = sağlanan kanıtlarla destekleniyor; bağımsız doğrulama garantisi değildir. disputed = çözülememiş çelişki. rejected = belirtilen kapsamda karşı kanıtla reddediliyor. unverified = yeterli kanıt/değerlendirme yok. Çoğunluk, aynı kaynak tekrarları ve model güveni kanıt değildir.
- Ret için somut gerekçe, açık karşı kaynak URL'leri, karşı kanıtın açıklaması ve eski iddianın neden geçersizleştiği gerekir. Eski destek kaynaklarını koru. Kısmi ret ise geçerli kalan kısmı ve koşulları yaz. Çözülmemiş itirazı sonraki aşamaya ve nihai rapora taşı. Bir ret eleştirilirse önceki ret gerekçesini de değerlendir.
- Sentezde yeni sayfa açamazsın: counter_evidence içinde yalnız sağlanan rapor/ek kanıtta bulunan bilgiyi kullan ve rapor kimliğine atıf ver. Kaynağın tam metni yoksa alıntıyı doğruladığını iddia etme. Araştırma aşamasında gerçekten açtığın yeni kaynakları URL ile ekleyebilirsin.
- Nihai yanıtta desteklenen bulgular, açık ihtilaflar, koşullu/kısmi retler ve incelenemeyen kritik iddialar ayrı görünmeli. Kanıt yetersizse kesin karar yerine koşullu karar ver; hangi yeni bulgunun kararı değiştireceğini belirt.
- Kör nokta taraması yap: sorunun yanlış varsayımı, eksik alternatif, seçim/yayın yanlılığı, aynı kaynağa bağımlılık, güncellik ve karşılaştırılamayan ölçüler. En az üç araştırılabilir kontrol sorusu üret; bilmediğin şeyleri uydurarak doldurma.
- Markdown raporun SONUNDA tam bir ```evidence-ledger JSON bloğu ekle (gizli düşünce zinciri değil, kısa kanıt gerekçeleri). Şema:
{"claims":[{"id":"CURRENT_STAGE:C001","statement":"Tek ve açık iddia; önceki kimlikte anlamı değiştirme","status":"supported|disputed|rejected|unverified","sources":["https://..."],"reason":"Kısa, denetlenebilir gerekçe ve kapsam/tarih","counter_sources":[],"counter_evidence":"Ret/itiraz varsa somut karşı kanıt ve rapor atfı; yoksa boş","limits":"Geçerli kalan kısım, tarih, belirsizlik ve karar koşulu"}],"blind_spots":["Kontrol sorusu"]}
Bu blokta olmayan önceki iddialar otomatik olarak reddedilmez veya doğrulanmaz; değerlendirilmemiş olarak raporlanır. Yapısal kontrolün geçmesi olgusal doğruluk garantisi değildir.'''


def source_id(url):
    return 'S-' + hashlib.sha256(url.encode()).hexdigest()[:16]


def source_register(stages):
    sources = {}
    for stage in stages:
        report = stage.get('report')
        if not report:
            continue
        for url in report.get('citations', []):
            sid = source_id(url)
            item = sources.setdefault(sid, {'id': sid, 'url': url, 'reports': [],
                                            'verification': 'URL recorded; source content/support not independently verified'})
            if stage['id'] not in item['reports']:
                item['reports'].append(stage['id'])
    return list(sources.values())


def register(stages):
    claims = {}
    for stage in stages:
        audit = stage.get('evidence_audit') or {}
        for claim in audit.get('assessments', []):
            ident = claim['id']
            entry = claims.setdefault(ident, {'id': ident, 'statement': claim['statement'],
                                             'original_stage': stage['id'], 'sources': [], 'assessments': []})
            for url in claim['sources']:
                if url not in entry['sources']:
                    entry['sources'].append(url)
            entry['assessments'].append({'stage': stage['id'], **claim})
    return {'sources': source_register(stages), 'claims': list(claims.values()),
            'limits': 'This register preserves model assessments, not established truth. Missing assessments never erase a claim.',
            'upstream_warnings': [{'stage': s['id'], 'warnings': s['evidence_audit']['warnings']}
                                  for s in stages if s.get('evidence_audit', {}).get('warnings')]}


def _urls(value):
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError('Kaynak listesi geçersiz.')
    for url in value:
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValueError()
        except ValueError:
            raise ValueError('Kaynak URL biçimi geçersiz.')
    return list(dict.fromkeys(value))


def audit_report(run, stage):
    """Validate a model-supplied ledger without rewriting its report or inferring truth."""
    prior = [s for s in run['stages'] if s['round'] < stage['round']]
    previous = register(prior)
    known = {c['id']: c for c in previous['claims']}
    known_urls = {s['url'] for s in previous['sources']}
    content = stage['report']['content']
    result = {'version': VERSION, 'assessments': [], 'warnings': [], 'missing_claim_ids': [],
              'unreferenced_prior_source_ids': [], 'blind_spots': [],
              'verification': 'structural_only; no source fetching or semantic entailment test'}
    blocks = ledger_blocks(content)
    try:
        if len(blocks) != 1:
            raise ValueError('Tek bir evidence-ledger bloğu bulunamadı.')
        ledger = json.loads(blocks[0])
        if not isinstance(ledger, dict) or not isinstance(ledger.get('claims'), list) or not ledger['claims']:
            raise ValueError('İddia kaydı eksik veya boş.')
        spots = ledger.get('blind_spots')
        if not isinstance(spots, list) or len(spots) < 3 or not all(isinstance(x, str) and x.strip() for x in spots):
            result['warnings'].append('En az üç kör nokta kontrol sorusu verilmedi.')
        else:
            result['blind_spots'] = spots
        seen = set()
        for raw in ledger['claims']:
            ident = raw.get('id') if isinstance(raw, dict) else None
            try:
                if not isinstance(ident, str) or ident in seen:
                    raise ValueError('Eksik/tekrarlanan iddia kimliği.')
                seen.add(ident)
                if ident not in known and not re.fullmatch(re.escape(stage['id']) + r':C[0-9]{3,6}', ident):
                    raise ValueError('Yeni iddia kimliği bu aşamaya ait değil.')
                if not all(isinstance(raw.get(k), str) for k in ('statement', 'status', 'reason', 'counter_evidence', 'limits')):
                    raise ValueError('İddianın gerekli alanları eksik.')
                if not raw['statement'].strip() or raw['status'] not in STATUSES or not raw['reason'].strip():
                    raise ValueError('İddia/durum/gerekçe geçersiz.')
                if ident in known and raw['statement'] != known[ident]['statement']:
                    raise ValueError('Önceki iddianın ifadesi değiştirildi; eski ifade korundu.')
                sources = _urls(raw.get('sources'))
                counter = _urls(raw.get('counter_sources'))
                if raw['status'] == 'supported' and not sources:
                    raise ValueError('Destekleniyor değerlendirmesinde kaynak yok.')
                if raw['status'] == 'rejected' and (not counter or not raw['counter_evidence'].strip()):
                    raise ValueError('Ret için somut karşı kanıt ve karşı kaynak eksik.')
                if stage['mode'] == 'account' and stage.get('account_profile') not in ('preliminary_research','research_review') and (set(sources + counter) - known_urls):
                    raise ValueError('Araçsız sentez, girdi paketinde olmayan kaynak ekledi.')
                old_sources = known.get(ident, {}).get('sources', [])
                result['assessments'].append({k: raw[k] for k in ('id','statement','status','reason','counter_evidence','limits')}
                    | {'sources': list(dict.fromkeys(old_sources + sources)), 'counter_sources': counter})
            except ValueError as exc:
                result['warnings'].append(str(ident) + ': ' + str(exc))
    except (ValueError, TypeError) as exc:
        result['warnings'].append(str(exc))
    assessed = {c['id'] for c in result['assessments']}
    result['missing_claim_ids'] = sorted(set(known) - assessed)
    if result['missing_claim_ids']:
        result['warnings'].append('Önceki iddialardan bazıları değerlendirilmedi; korunuyor ve ret sayılmıyor.')
    current_urls = set(stage['report'].get('citations', []))
    result['unreferenced_prior_source_ids'] = [s['id'] for s in previous['sources'] if s['url'] not in current_urls]
    result['source_coverage_note'] = 'URL omission is tracked, not proof that a claim is false or that every URL must be cited in prose.'
    return result


def audit_appendix(run, stage):
    audit = stage.get('evidence_audit')
    if not audit:
        return ''
    lines = ['\n\n---\n## Yerel kanıt kontrolü',
             'Bu ek uygulama tarafından üretildi; raporun özgün metni değiştirilmedi. Yapısal kontrol, doğruluk veya kaynak doğrulaması değildir.']
    if audit['warnings']:
        lines += ['**İnceleme gerekli:**'] + ['- '+w for w in audit['warnings']]
    else:
        lines += ['İddia kaydı biçimsel kontrolleri geçti. Kanıtların gerçekten iddiayı desteklemesi ayrıca değerlendirilmelidir.']
    if audit['missing_claim_ids']:
        lines += ['Değerlendirilmeden korunan iddialar: '+', '.join(audit['missing_claim_ids'])]
    if stage['round'] == 4:
        complete = register(run['stages'])
        lines += ['\n### Önceki aşamalardan gelen kontrol uyarıları']
        lines += ['- '+x['stage']+': '+'; '.join(x['warnings']) for x in complete['upstream_warnings'] if x['stage'] != stage['id']]
        lines += ['\n### Korunan kaynak envanteri',
                  'URL’ler raporlardan kaydedilmiştir; erişilebilirlik, bağımsızlık veya iddia desteği doğrulanmış sayılmaz.']
        lines += ['- '+s['id']+' — '+s['url']+' — '+', '.join(s['reports']) for s in complete['sources']]
        lines += ['\n### Korunan iddia geçmişi']
        for claim in complete['claims']:
            lines += ['- '+claim['id']+': '+claim['statement']+' — '+
                      '; '.join(a['stage']+'='+a['status'] for a in claim['assessments'])]
    return '\n'.join(lines)
