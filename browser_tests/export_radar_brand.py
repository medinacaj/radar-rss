"""Export browser-rendered sizes from the generated brand masters, offline.

Run with the development Playwright environment; production has no dependency.
"""
import base64
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MASTERS = ROOT / 'assets/brand'
WEB = ROOT / 'web'


def export():
    logo = base64.b64encode((MASTERS / 'radar-rss-symbol-master.png').read_bytes()).decode()
    social = base64.b64encode((MASTERS / 'radar-rss-social-master.png').read_bytes()).decode()
    targets = [
        ('radar-rss-mark.png', 128, 128, 'transparent'),
        ('radar-rss-favicon-64.png', 64, 64, 'rounded'),
        ('radar-rss-icon-192.png', 192, 192, 'rounded'),
        ('radar-rss-icon-512.png', 512, 512, 'rounded'),
        ('radar-rss-maskable-512.png', 512, 512, 'maskable'),
        ('radar-rss-apple-touch-icon.png', 180, 180, 'square'),
        ('radar-rss-social-card.png', 1200, 630, 'social'),
    ]
    with sync_playwright() as driver:
        options = {'headless': True}
        if os.environ.get('RADAR_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['RADAR_CHROMIUM_EXECUTABLE']
        browser = driver.chromium.launch(**options)
        page = browser.new_page()
        for name, width, height, kind in targets:
            encoded = page.evaluate('''async ({source,width,height,kind})=>{
                const image=new Image();image.src='data:image/png;base64,'+source;await image.decode();
                const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
                const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
                if(kind!=='transparent'&&kind!=='social'){
                    ctx.fillStyle='#f4f7f6';
                    if(kind==='rounded'){ctx.beginPath();ctx.roundRect(0,0,width,height,width*.21);ctx.fill();}
                    else ctx.fillRect(0,0,width,height);
                }
                const inset=kind==='maskable'?width*.1:0;
                ctx.drawImage(image,inset,inset,width-inset*2,height-inset*2);
                return canvas.toDataURL('image/png').split(',')[1];
            }''', {'source': social if kind == 'social' else logo,
                   'width': width, 'height': height, 'kind': kind})
            (WEB / name).write_bytes(base64.b64decode(encoded))
        browser.close()
    print(json.dumps({'exports': [name for name, *_ in targets]}, ensure_ascii=False))


if __name__ == '__main__':
    export()
