#!/usr/bin/env python3
"""Pre-render check for a Night story.json (run before tools/make_video.py).
Usage: python3 tools/check_story.py stories/<id>/story.json [...]
Exit 1 = fix before rendering."""
import json, re, sys
bad = 0
for path in sys.argv[1:]:
    s = json.load(open(path)); errs = []
    sc = s['scenes']
    words = sum(len(x.get('narration', '').split()) for x in sc)
    if not 160 <= words <= 250: errs.append(f'words {words} (target 160-250)')
    first = re.split(r'(?<=[.!?])\s+', sc[0]['narration'].strip())[0]
    if s.get('hook_text', '').strip() not in (first, sc[0]['narration'].strip()): errs.append('hook_text differs from first sentence')
    for i, x in enumerate(sc):
        nar = x.get('narration', '').lower()
        for o in x.get('overlays', []):
            t = o.get('text', '')
            if o.get('kind') == 'choice':
                if len(t) > 24: errs.append(f'scene {i}: choice text {len(t)} chars (max 24, one line)')
                if len(re.split(r'\s+or\s+', t)) != 2: errs.append(f'scene {i}: choice needs two options with "or"')
            w = o.get('at_word')
            if w and w.lower() not in re.findall(r"[a-z']+", nar): errs.append(f'scene {i}: at_word "{w}" not in narration')
        for f in x.get('sfx', []):
            w = f.get('at_word')
            if w and w.lower() not in re.findall(r"[a-z']+", nar): errs.append(f'scene {i}: sfx at_word "{w}" not in narration')
    cap = s.get('post', {}).get('caption', '')
    if re.search(r'\b[ap]\.m\.', json.dumps(s), re.I): errs.append('a.m./p.m. in text (write "in the morning")')
    if len(re.findall(r'#\w+', cap)) != 5: errs.append('caption needs exactly 5 hashtags')
    print(('OK   ' if not errs else 'FAIL ') + path + (' | ' + '; '.join(errs) if errs else ''))
    bad += bool(errs)
sys.exit(1 if bad else 0)
