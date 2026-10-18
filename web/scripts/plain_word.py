from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import hashlib

ROOT = Path('/Users/loise/Documents/資料庫')
SRC = ROOT / '參考資料/Fitness_Tracking_Management_System_SRS_中文版_PHP評分規範版.docx'
OUT = ROOT / 'web/output/specification/Fitness_Tracking_Management_System_SRS_中文版_純文字排版版.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ns = {'w': W}
def q(n): return '{'+W+'}'+n
before = hashlib.sha256(SRC.read_bytes()).hexdigest()
with ZipFile(SRC) as z:
    entries = {n:z.read(n) for n in z.namelist()}
original = E.fromstring(entries['word/document.xml'])
texts = original.xpath('//w:t/text()', namespaces=ns)
for name, data in list(entries.items()):
    if not name.startswith('word/') or not name.endswith('.xml'):
        continue
    root = E.fromstring(data)
    # Remove the source's empty decorative floating rectangle, not diagram images.
    for el in root.xpath('//w:drawing', namespaces=ns):
        if (el.xpath('.//*[local-name()="wsp"]')
                and not el.xpath('.//*[local-name()="t" or local-name()="blip"]')):
            el.getparent().remove(el)
    # Keep font sizes, indentation, pagination, native fields, tables and figures.
    # Only remove visual theme treatment; force dark table-header text as well.
    for el in root.xpath('//w:shd | //w:highlight | //w:pBdr | //w:pgBorders | //w:background | //w:attachedTemplate', namespaces=ns):
        el.getparent().remove(el)
    for el in root.xpath('//w:color', namespaces=ns):
        el.attrib.clear()
        el.set(q('val'), '000000')
    for el in root.xpath('//w:tblBorders/* | //w:tcBorders/*', namespaces=ns):
        el.set(q('color'), '000000')
        for a in ('themeColor','themeTint','themeShade'):
            el.attrib.pop(q(a), None)
    if name.startswith('word/header'):
        # Remove repeating report branding, retain the body title and page numbers.
        for el in root.xpath('//w:t', namespaces=ns):
            el.text = ''
    if name == 'word/settings.xml':
        for el in root.xpath('//w:updateStylesOnOpen', namespaces=ns):
            el.getparent().remove(el)
    entries[name] = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(OUT, 'w', ZIP_DEFLATED) as z:
    for name, data in entries.items():
        z.writestr(name, data)
with ZipFile(OUT) as z:
    result = E.fromstring(z.read('word/document.xml'))
    assert result.xpath('//w:t/text()', namespaces=ns) == texts
    assert not result.xpath('//w:shd | //w:highlight | //w:pBdr', namespaces=ns)
assert hashlib.sha256(SRC.read_bytes()).hexdigest() == before
print({'output':str(OUT),'body_text_unchanged':True,'source_unchanged':True,'tables':len(result.xpath('//w:tbl',namespaces=ns))})
