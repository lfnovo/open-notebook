import { beforeAll, describe, expect, it, vi } from 'vitest'
import { webcrypto } from 'node:crypto'
import { strToU8, zipSync } from 'fflate'
import { checkDocxArchive, composeBrief, documentKind, extractDocx, readDocument } from './brief-documents'

beforeAll(()=>vi.stubGlobal('crypto',webcrypto))
const docx = (extras: Record<string, Uint8Array> = {}) => zipSync({
  '[Content_Types].xml':strToU8('<Types/>'),
  'word/document.xml':strToU8('<w:document xmlns:w="urn:word"><w:body><w:p><w:r><w:t>Birinci kanıt</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>42</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:t>Son koşul.</w:t></w:r></w:p></w:body></w:document>'),
  ...extras,
})

describe('Document type and content admission',()=>{
  it('accepts multiple supported types and case-insensitive suffixes',()=>{
    for(const suffix of ['MD','markdown','txt','csv','json','yaml','yml','pdf','docx'])expect(documentKind('Research.'+suffix)).toBe(suffix.toLowerCase())
  })
  it('rejects executables, macros, disguised double extensions, unsafe names and unsupported files',()=>{
    for(const name of ['run.exe','report.exe.md','data.docm','file.sh.txt','a.zip','a/b.md','a\\b.md','a\nb.md'])expect(()=>documentKind(name)).toThrow('briefFileBlocked')
    expect(()=>documentKind('image.png')).toThrow('briefFileType')
    expect(()=>documentKind('no-extension')).toThrow('briefFileType')
  })
  it('preserves DOCX paragraphs, table values, footnotes and hyperlink targets',()=>{
    const text=extractDocx(docx({'word/footnotes.xml':strToU8('<w:footnotes xmlns:w="urn:word"><w:p><w:r><w:t>İstisna</w:t></w:r></w:p></w:footnotes>'),'word/_rels/document.xml.rels':strToU8('<Relationships><Relationship Type="urn:test/hyperlink" Target="https://example.org/evidence"/></Relationships>')}))
    for(const item of ['Birinci kanıt','42','Son koşul.','İstisna','https://example.org/evidence'])expect(text).toContain(item)
  })
  it('rejects macros, embedded objects, paths and missing Word parts',()=>{
    for(const name of ['word/vbaProject.bin','word/embeddings/oleObject1.bin','../outside'])expect(()=>checkDocxArchive(docx({[name]:strToU8('data')}))).toThrow('briefFileBlocked')
    expect(()=>checkDocxArchive(zipSync({'ordinary.txt':strToU8('text')}))).toThrow('briefFileSignature')
  })
  it('rejects forged expanded sizes before decompression',()=>{
    const bytes=docx(),view=new DataView(bytes.buffer)
    for(let i=0;i<bytes.length-46;i++)if(view.getUint32(i,true)===0x02014b50){view.setUint32(i+24,50*1024*1024,true);break}
    expect(()=>checkDocxArchive(bytes)).toThrow('briefArchiveTooLarge')
  })
  it('rejects DTD/entity declarations rather than resolving external XML',()=>{
    expect(()=>extractDocx(docx({'word/document.xml':strToU8('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///private">]><a>&x;</a>')}))).toThrow('briefFileBlocked')
  })
  it('checks renamed binary signatures in text files',async()=>{
    const bytes=strToU8('MZexecutable')
    await expect(readDocument({name:'evidence.txt',size:bytes.length,arrayBuffer:async()=>bytes.buffer} as File)).rejects.toThrow('briefFileSignature')
  })
  it('combines every document without deleting its text and refuses failed documents',()=>{
    const files=['one.md','two.csv'].map((name,i)=>({id:String(i),name,size:20,text:'Exact content '+i+'\n',sha256:'hash'+i,kind:'txt'}))
    const combined=composeBrief('Investigate',files)
    for(const f of files){expect(combined).toContain(f.name);expect(combined).toContain(f.text);expect(combined).toContain(f.sha256)}
    expect(()=>composeBrief('',[{...files[0],error:'failed'}])).toThrow('briefFilesNeedAttention')
  })
})
