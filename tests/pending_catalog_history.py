"""Scope immutable catalog snapshots without excluding unknown additions."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def before_pending_expansions(sources, keep=None):
    excluded=set()
    for kind,filename in [('business','business-sources-verification.json'),('monagas','monagas-verification.json')]:
        if kind != keep:
            excluded.update(row['feed'] for row in json.loads((ROOT/'sources'/filename).read_text())['sources'])
    return [s for s in sources if s['url'] not in excluded and (keep=='elevenlabs' or s['name']!='RADAR — ElevenLabs | video y herramientas IA')]
