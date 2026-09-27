"""Deterministic event/condition/action policy; never adjudicates factual truth.

Rules are typed, versioned code, not executable expressions from imported text.
Warnings preserve evidence. Only integrity and capacity failures block submission.
"""
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import Callable
import hashlib
import json

from packet_markdown import compact_claims, expand_claims, ledger_blocks

POLICY_VERSION = 'research-eca-v1'


@dataclass(frozen=True)
class Rule:
    id: str
    condition: Callable[[dict], bool]
    action: str
    severity: str
    message: str
    metric: str

    def evaluate(self, facts):
        if not self.condition(facts):
            return None
        return {'id': self.id, 'action': self.action, 'severity': self.severity,
                'message': self.message, 'evidence': {self.metric: facts[self.metric]}}


RULES = (
    Rule('ECA-001', lambda f: f['duplicate_source_entries'] > 0, 'reference_exact_duplicate', 'info',
         'Birebir aynı URL kaynakçada bir kez temsil edilir; hangi raporlarda geçtiği ve satır içi atıflar korunur. URL sayısı bağımsız doğrulama sayısı değildir.', 'duplicate_source_entries'),
    Rule('ECA-002', lambda f: f['referenced_assessments'] > 0, 'reference_exact_duplicate', 'info',
         'Raporda zaten bulunan değerlendirmeler açık referansla temsil edilir. Kaynak birleşimleri ve değişen alanlar ayrıca korunur; ters dönüşüm birebir doğrulanır.', 'referenced_assessments'),
    Rule('ECA-003', lambda f: bool(f['duplicate_reports']), 'preserve_and_warn', 'warning',
         'Aynı rapor metni birden fazla aşamada bulundu. Metinler ve kökenleri korunuyor; bunları bağımsız doğrulama saymayın.', 'duplicate_reports'),
    Rule('ECA-004', lambda f: bool(f['duplicate_attachments']), 'preserve_and_warn', 'warning',
         'Birebir aynı ek kanıt birden fazla yerde bulundu. Rapor bağlantıları korunuyor; tekrarlar ek kanıt gücü sayılmaz.', 'duplicate_attachments'),
    Rule('ECA-005', lambda f: bool(f['ambiguous_ledgers']), 'preserve_and_warn', 'warning',
         'Bir raporda farklı kanıt kayıtları veya yinelenen iddia kimlikleri var. Belirsiz kayıtlarda referansla tekilleştirme yapılmaz; içerik ve itirazlar korunur.', 'ambiguous_ledgers'),
    Rule('ECA-006', lambda f: bool(f['conflicting_claim_ids']), 'preserve_and_warn', 'warning',
         'Aynı iddia için farklı değerlendirmeler bulundu. Geçmiş silinmedi; son değerlendirme veya çoğunluk otomatik olarak doğru sayılmaz.', 'conflicting_claim_ids'),
    Rule('ECA-007', lambda f: f['upstream_warning_count'] > 0, 'preserve_and_warn', 'warning',
         'Önceki raporlarda yapısal kanıt uyarıları var. Eksik değerlendirme ret değildir; gerekçesiz ret eski kanıtın yerine geçmez.', 'upstream_warning_count'),
    Rule('ECA-008', lambda f: bool(f['unknown_research_dates']), 'preserve_and_warn', 'warning',
         'Araştırma tarihi bildirilmeyen raporlar var. Kayıt zamanı araştırma tarihi kabul edilmez; güncellik doğrulanmış sayılmaz.', 'unknown_research_dates'),
    Rule('ECA-009', lambda f: bool(f['after_target_date']), 'preserve_and_warn', 'warning',
         'Hedef tarihten sonra araştırılmış raporlar var. İçerik korunur; tarih farkı sonuçta ayrıca değerlendirilmelidir.', 'after_target_date'),
    Rule('ECA-010', lambda f: f['utilization'] >= .85 and not f['over_limit'], 'warn_near_limit', 'warning',
         'Girdi bütçesinin en az %85’i kullanılıyor. Raporlar korunur; sonraki turlarda oluşacak büyüme ayrıca kontrol edilir.', 'utilization'),
    Rule('ECA-011', lambda f: f['over_limit'], 'block_submission', 'error',
         'Tam girdi paketi hesaplanan bağlam bütçesini aşıyor. Model çağrısı ve otomatik tekrar yapılmaz; metin kesilmez.', 'counted_tokens'),
    Rule('ECA-012', lambda f: not f['lossless_index'], 'block_submission', 'error',
         'Referanslardan geri kurulan iddia geçmişi özgün kayıtla uyuşmuyor. Gönderim durduruldu; hiçbir kayıt silinmedi.', 'lossless_index'),
    Rule('ECA-013', lambda f: bool(f['attachment_integrity_errors']), 'block_submission', 'error',
         'Ek kanıt içeriği kayıtlı SHA-256 ile uyuşmuyor. Bozulmuş kanıtla model isteği yapılmaz.', 'attachment_integrity_errors'),
    Rule('ECA-014', lambda f: not f['calibrated'], 'preserve_and_warn', 'warning',
         'Bu sağlayıcı için çalıştırıcı kimliğine bağlı token kalibrasyonu yok. Sayım tahmindir; kesin sağlayıcı ölçümü olarak sunulmaz.', 'calibrated'),
)


class ResearchRules:
    """Read-only preview and the same enforced pre-submission decision."""
    @staticmethod
    def provider_check(expected, actual):
        mismatch = bool(expected) and actual != expected
        return {'version': POLICY_VERSION, 'event': 'provider_preflight', 'rules_evaluated': 1,
                'blocked': mismatch, 'block_status': 'calibration_required' if mismatch else None,
                'factual_verification': False, 'findings': [{
                    'id': 'ECA-015', 'action': 'block_submission', 'severity': 'error',
                    'message': 'Model, CLI sürümü veya çalıştırma talimatları değişti; eski token kalibrasyonu kullanılarak istek gönderilmedi. Kalibrasyon yenilenmeli.',
                    'evidence': {'expected_fingerprint': expected, 'actual_fingerprint': actual},
                }] if mismatch else []}

    def evaluate(self, packet, budget, event='packet_prepared', account=True, compact=True):
        reports = packet['reports']
        claims = packet.get('evidence_register', {}).get('claims', [])
        indexed = compact_claims(claims, reports) if compact else claims
        groups = defaultdict(list)
        attachments = defaultdict(list)
        ambiguous, invalid_attachments = [], []
        for report in reports:
            stage = report['stage']
            groups[hashlib.sha256(report['content'].encode()).hexdigest()].append(stage)
            blocks = ledger_blocks(report['content'])
            if len(blocks) > 1:
                ambiguous.append(stage)
            elif blocks:
                try:
                    values = json.loads(blocks[0]).get('claims', [])
                    ids = [c.get('id') for c in values if isinstance(c, dict)]
                    if any(not isinstance(ident,str) for ident in ids) or any(n > 1 for n in Counter(ident for ident in ids if isinstance(ident,str)).values()):
                        ambiguous.append(stage)
                except (ValueError, TypeError, AttributeError):
                    ambiguous.append(stage)
            for i, evidence in enumerate(report['evidence']):
                actual = hashlib.sha256(evidence['content'].encode()).hexdigest()
                ref = f'{stage}:attachment:{i}'
                attachments[actual].append(ref)
                if evidence.get('sha256') and evidence['sha256'] != actual:
                    invalid_attachments.append(ref)
        entries = [u for report in reports for u in report['citations']]
        facts = {
            'duplicate_source_entries': len(entries) - len(set(entries)),
            'referenced_assessments': sum('report_claim' in a for c in indexed for a in c['assessments']) if compact else 0,
            'duplicate_reports': [v for v in groups.values() if len(v) > 1],
            'duplicate_attachments': [v for v in attachments.values() if len(v) > 1],
            'ambiguous_ledgers': ambiguous,
            'conflicting_claim_ids': [c['id'] for c in claims if len({a['status'] for a in c['assessments']}) > 1],
            'upstream_warning_count': sum(len(v['warnings']) for v in packet.get('evidence_register', {}).get('upstream_warnings', [])),
            'unknown_research_dates': [r['stage'] for r in reports if r['provenance'] in ('web_deep_research_import','browser_deep_research') and not r['researched_at']],
            'after_target_date': [r['stage'] for r in reports if r['researched_at'] and r['researched_at'] > packet['as_of']],
            'utilization': budget.get('utilization', 0) if account else 0,
            'counted_tokens': budget.get('counted_tokens', budget.get('estimated_tokens', 0)),
            'over_limit': account and budget.get('estimated_tokens', 0) > budget['automatic_input_limit'],
            'lossless_index': expand_claims(indexed, reports) == claims if compact else True,
            'attachment_integrity_errors': invalid_attachments,
            'calibrated': not account or bool(budget.get('token_margin', {}).get('calibration_fingerprint')),
        }
        findings = [finding for rule in RULES if (finding := rule.evaluate(facts))]
        if not compact:
            for finding in findings:
                if finding['id'] == 'ECA-001':
                    finding.update(action='preserve_and_warn',severity='warning',
                        message='Tekrarlanan kaynak URL’leri bulundu. Bu eski paketin biçimi korunuyor; tekrarlar bağımsız kanıt sayılmaz.')
        integrity = not facts['lossless_index'] or bool(invalid_attachments)
        return {'version': POLICY_VERSION, 'event': event, 'rules_evaluated': len(RULES),
                'blocked': integrity or facts['over_limit'],
                'block_status': 'integrity_error' if integrity else ('context_limit' if facts['over_limit'] else None),
                'findings': findings, 'factual_verification': False}
