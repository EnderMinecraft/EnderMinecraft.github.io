#!/usr/bin/env python3
"""Split a textbook PDF into one clean .txt file per chapter, ready to paste into an AI prompt.

Needs: python3, pypdf, and poppler's `pdftotext`. For scanned books also: `pdftoppm` (poppler) and `tesseract`.
  pip install pypdf

Usage:
  python3 tools/pdf-to-chapters.py book.pdf out/                      # chapters = top-level bookmarks
  python3 tools/pdf-to-chapters.py book.pdf out/ --pages 1-14,15-32   # or give 1-based page ranges yourself
  python3 tools/pdf-to-chapters.py book.pdf out/ --lang vie           # OCR language for scanned pages (tesseract code)
  python3 tools/pdf-to-chapters.py book.pdf out/ --list               # just show the detected chapters

Writes out/ch01.txt, out/ch02.txt ... and out/chapters.json (titles + page ranges).
A page with almost no text layer is treated as scanned and OCR'd automatically. Always skim the output:
OCR and multi-column layouts make mistakes, and the text is only as good as this step."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from collections import Counter
from pypdf import PdfReader

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def outline_chapters(reader):
    """Top-level bookmarks -> [(title, first_page_index)]"""
    out = []
    def walk(items):
        for it in items:
            if isinstance(it, list): continue          # skip children: we only want the top level
            try: out.append((str(it.title).strip(), reader.get_destination_page_number(it)))
            except Exception: pass
    walk(reader.outline)
    out = sorted({p: t for t, p in out}.items())      # one chapter per start page
    return [(t, p) for p, t in out]

def page_text(pdf, n, lang, scratch):
    """Text of 1-based page n; OCR if there is no usable text layer."""
    t = run(['pdftotext', '-f', str(n), '-l', str(n), '-enc', 'UTF-8', pdf, '-']).stdout
    if len(t.strip()) >= 25: return t
    if not (shutil.which('pdftoppm') and shutil.which('tesseract')): return t
    base = os.path.join(scratch, 'p%d' % n)
    run(['pdftoppm', '-f', str(n), '-l', str(n), '-r', '300', '-png', pdf, base])
    img = [f for f in os.listdir(scratch) if f.startswith('p%d-' % n) and f.endswith('.png')]
    if not img: return t
    return run(['tesseract', os.path.join(scratch, img[0]), '-', '-l', lang]).stdout

def clean(pages):
    """Drop running headers/footers and page numbers, rejoin hyphenated and wrapped lines."""
    lines = [[l.strip() for l in p.splitlines()] for p in pages]
    freq = Counter(l for pg in lines for l in set(pg) if l)
    repeated = {l for l, c in freq.items() if len(pages) >= 2 and c >= max(2, len(pages) * 0.5) and len(l) < 80}
    out = []
    for pg in lines:
        keep = [l for l in pg if l not in repeated and not re.fullmatch(r'(page\s*)?[-–]?\s*\d{1,4}\s*[-–]?', l, re.I)]
        out.append('\n'.join(keep))
    text = '\n\n'.join(out)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)           # hyphenation at line end
    text = re.sub(r'(?<![.!?:;\n])\n(?!\n|[-•*\d])', ' ', text)  # wrapped lines -> one paragraph
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf'); ap.add_argument('outdir')
    ap.add_argument('--pages', help='1-based inclusive ranges, one per chapter, e.g. 1-14,15-32')
    ap.add_argument('--lang', default='eng', help='tesseract language for scanned pages (eng, vie, ...)')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    if not shutil.which('pdftotext'): sys.exit('pdftotext (poppler) is required.')
    reader = PdfReader(a.pdf); total = len(reader.pages)
    if a.pages:
        chs = []
        for i, r in enumerate(a.pages.split(','), 1):
            s, e = (int(x) for x in r.split('-')); chs.append(('Chapter %d' % i, s, min(e, total)))
    else:
        ol = outline_chapters(reader)
        if not ol: sys.exit('No bookmarks found. Give page ranges with --pages 1-14,15-32')
        chs = [(t, p + 1, (ol[i + 1][1] if i + 1 < len(ol) else total)) for i, (t, p) in enumerate(ol)]
        chs = [(t, s, max(s, e if i + 1 == len(chs) else e)) for i, (t, s, e) in enumerate(chs)]
    for i, (t, s, e) in enumerate(chs, 1): print('%02d  pages %d-%d  %s' % (i, s, e, t))
    if a.list: return
    os.makedirs(a.outdir, exist_ok=True); scratch = tempfile.mkdtemp(); manifest = []
    for i, (t, s, e) in enumerate(chs, 1):
        pages = [page_text(a.pdf, n, a.lang, scratch) for n in range(s, e + 1)]
        ocr = sum(1 for n in range(len(pages)) if len(pages[n].strip()) < 25)
        txt = clean(pages); name = 'ch%02d.txt' % i
        open(os.path.join(a.outdir, name), 'w', encoding='utf-8').write(txt)
        manifest.append({'file': name, 'title': t, 'pages': [s, e], 'chars': len(txt), 'emptyPages': ocr})
        print('wrote %s  %d characters%s' % (name, len(txt), '  (WARNING: %d page(s) gave no text)' % ocr if ocr else ''))
    json.dump(manifest, open(os.path.join(a.outdir, 'chapters.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    shutil.rmtree(scratch, ignore_errors=True)

if __name__ == '__main__': main()
