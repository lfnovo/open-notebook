"""Read report files locally, retaining their original bytes separately."""
import io
from pathlib import Path
import zipfile
from pypdf import PdfReader
from docx import Document

MAX_BYTES=8*1024*1024
MAX_TEXT=4*1024*1024


def extract(filename, data):
    if len(data)>MAX_BYTES:raise ValueError('Bir dosya en fazla 8 MB olabilir.')
    suffix=Path(filename).suffix.lower()
    if suffix in ('.md','.txt','.markdown'):
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:raise ValueError('Metin dosyası UTF-8 biçiminde olmalı.')
    elif suffix=='.pdf':
        reader=PdfReader(io.BytesIO(data))
        if reader.is_encrypted:raise ValueError('Şifreli PDF yerine açık PDF veya Markdown yükleyin.')
        if len(reader.pages)>250:raise ValueError('PDF en fazla 250 sayfa olabilir.')
        parts=[]
        for page in reader.pages:
            parts.append(page.extract_text() or '')
            for annotation in page.get('/Annots',[]):
                obj=annotation.get_object();uri=obj.get('/A',{}).get('/URI')
                if uri:parts.append(str(uri))
        text='\n\n'.join(parts)
    elif suffix=='.docx':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist())>40*1024*1024:raise ValueError('Açılmış belge boyutu çok büyük.')
        document=Document(io.BytesIO(data));parts=[]
        for item in document.iter_inner_content():
            if hasattr(item,'text'):parts.append(item.text)
            elif hasattr(item,'rows'):parts.extend(' | '.join(c.text for c in r.cells) for r in item.rows)
        parts.extend(rel.target_ref for rel in document.part.rels.values() if rel.reltype.endswith('/hyperlink'))
        text='\n\n'.join(parts)
    else:raise ValueError('Desteklenen dosyalar: .md, .txt, .pdf, .docx')
    if len(text.encode())>MAX_TEXT:raise ValueError('Çıkarılan metin çok büyük; dosyayı bölerek ek kanıt olarak yükleyin.')
    if not text.strip():raise ValueError('Dosyadan metin çıkarılamadı. Taranmış PDF için önce OCR uygulayın veya raporu metin olarak yapıştırın.')
    return text
