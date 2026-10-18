"""Cache correct pages in the editable native Word TOC after PDF rendering."""
from pathlib import Path
import json
import re
import sys
from docx import Document
from pypdf import PdfReader

root=Path(__file__).resolve().parents[1]
path=root/'output/specification/Fitness_Tracking_Management_System_SRS_中文版.docx'
headings=json.loads((root/'tmp/srs_teacher/headings.json').read_text())
pdf=PdfReader(sys.argv[1])
normalize=lambda text: re.sub(r'\s+','',text)
page_map={}
for i,page in enumerate(pdf.pages,1):
    lines=page.extract_text().splitlines()
    for text,level,name in headings:
        if level>2: continue
        target=normalize(text)
        for n in range(len(lines)):
            if any(normalize(''.join(lines[n:n+count]))==target for count in (1,2,3)):
                page_map[text]=i
                break
missing=[t for t,l,n in headings if l<=2 and t not in page_map]
if missing: raise RuntimeError('Headings not located in PDF: '+str(missing))
d=Document(path)
updated=0
for p in d.paragraphs:
    if p.style.name.lower() not in ('toc 1','toc 2'): continue
    texts=p._p.xpath('.//w:t')
    title=texts[0].text
    if title not in page_map: raise RuntimeError('TOC entry not found: '+title)
    texts[-1].text=str(page_map[title])
    updated+=1
d.save(path)
(root/'tmp/srs_teacher/toc_pages.json').write_text(json.dumps(page_map,ensure_ascii=False,indent=2))
print(json.dumps({'updated_toc_entries':updated,'pdf_pages':len(pdf.pages)},ensure_ascii=False))
