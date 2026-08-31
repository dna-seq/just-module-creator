"""Minimal stdlib xlsx row reader - the plugin can describe a workbook but not read a cell of it."""
import zipfile, re, sys
from xml.etree import ElementTree as ET
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def _col(ref):
    m = re.match(r'([A-Z]+)', ref or '')
    if not m: return 0
    n = 0
    for ch in m.group(1): n = n*26 + (ord(ch)-64)
    return n-1

def read(path, sheet_name=None):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in root.findall(f'{NS}si'):
            shared.append(''.join(t.text or '' for t in si.iter(f'{NS}t')))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rmap = {r.get('Id'): r.get('Target') for r in rels}
    out = {}
    for sh in wb.find(f'{NS}sheets'):
        name = sh.get('name')
        if sheet_name and name != sheet_name: continue
        tgt = rmap.get(sh.get(f'{RNS}id'), '')
        if not tgt.startswith('xl/'): tgt = 'xl/' + tgt.lstrip('/')
        rows = []
        root = ET.fromstring(z.read(tgt))
        for r in root.iter(f'{NS}row'):
            cells = {}
            for c in r.findall(f'{NS}c'):
                idx = _col(c.get('r')); t = c.get('t')
                if t == 'inlineStr':
                    v = ''.join(x.text or '' for x in c.iter(f'{NS}t'))
                else:
                    ve = c.find(f'{NS}v'); v = ve.text if ve is not None else None
                    if t == 's' and v is not None: v = shared[int(v)]
                cells[idx] = v
            width = max(cells)+1 if cells else 0
            rows.append([cells.get(i) for i in range(width)])
        out[name] = rows
    return out
