"""Deterministic query intent, separate from retrieval and provider integrations."""
import re
import unicodedata

TEXT_EXT = set('txt md markdown rst csv tsv json jsonl yaml yml toml xml html htm css scss js jsx ts tsx py rs go java c h cpp sql sh zsh fish swift kt rb r tex log php mjs cjs svg twig astro vue svelte ini conf cfg properties po'.split())
OFFICE_EXT = {'pdf', 'docx', 'xlsx', 'pptx'}
IMAGE_EXT = {'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'webp', 'heic'}
DOC_EXT = TEXT_EXT | OFFICE_EXT | IMAGE_EXT
GROUPS = [('strateji','strategy','strategic'),('belge','dokuman','dokume','document','documentation'),('rapor','report'),('plan','roadmap','yolharita'),('mimari','architecture'),('butce','budget'),('sozlesme','contract','agreement'),('toplanti','meeting'),('fatura','invoice'),('arastirma','research'),('finans','finance','financial'),('pazarlama','marketing'),('guvenlik','security')]
STOP = set('ben benim bana bir ve veya ile icin nasil hangi nerede nerde nereden bul bulur bulabilir dosya dosyam dosyalar file files my where is the a of do you can find please dokuman document belgeler'.split())
# Bare programming-language words (go, c, r, ...) are not file constraints.
BARE_FORMATS = OFFICE_EXT | IMAGE_EXT | {'md','markdown','txt','csv','tsv','json','jsonl','mp4','mp3','zip'}

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower().replace('ı','i')) if not unicodedata.combining(c))

def query_terms(query):
    text = normalized(query)
    formats = re.findall(r'(?<!\w)(?:filetype:|ext:|\.)([a-z0-9]+)\b', text)
    formats = [f for f in formats if f in DOC_EXT | BARE_FORMATS]
    text = re.sub(r'(?<!\w)(?:filetype:|ext:|\.)([a-z0-9]+)\b', ' ', text)
    words = re.findall(r'[a-z0-9]+', text)[:40]
    formats += [w for w in words if w in BARE_FORMATS]
    terms = []
    for word in words:
        if word in STOP or word in formats: continue
        group = next((g for g in GROUPS if any(word.startswith(x) for x in g)), None)
        if group and group[0] == 'belge': continue
        terms.extend(group or [word])
    return list(dict.fromkeys(terms)), list(dict.fromkeys(formats))

def wants_document(query):
    return bool(re.search(r'\b(dok[uü][mü]an|dokuman|dokume|belge|document|report|rapor)', normalized(query)))
