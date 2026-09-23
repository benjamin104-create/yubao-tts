#!/usr/bin/env python3
"""Package ImageGen masters; retain RGBA gradients instead of pixel quantization.

Only crops/normalizes supplied artwork. Never invents detail by enlarging legacy
sprites. The manifest records source rectangles for reproducible review.
"""
import json
import pathlib
from collections import deque
from PIL import Image, ImageEnhance, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'art_raw' / 'hd-v18'
OUT = ROOT / 'web' / 'art-hd'


def subject_box(im):
    """Find the main connected silhouette, excluding neighboring cell flecks."""
    w,h=im.size
    mask=bytearray(1 if a>32 else 0 for a in im.getchannel('A').tobytes())
    best=(0,None)
    for start in range(w*h):
        if not mask[start]:
            continue
        mask[start]=0
        queue=deque([start]);area=0;x0=w;y0=h;x1=y1=0
        while queue:
            p=queue.popleft();y,x=divmod(p,w);area+=1
            x0=min(x0,x);x1=max(x1,x);y0=min(y0,y);y1=max(y1,y)
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<w and 0<=ny<h:
                    k=ny*w+nx
                    if mask[k]:mask[k]=0;queue.append(k)
        if area>best[0]:best=(area,(max(0,x0-1),max(0,y0-1),min(w,x1+2),min(h,y1+2)))
    return best[1]


def gutters(im, count, axis):
    """Find transparent gutters near the nominal grid, not assumed cell edges.

    Image models do not produce exact cell geometry. Cutting every 25% can
    amputate a wing or blade even when the whole figure exists in the master.
    Only searches locally; asset ordering cannot change silently.
    """
    mask=im.getchannel('A').point(lambda a: 255 if a>80 else 0)
    n=im.width if axis==0 else im.height
    # Compute occupancy once, instead of allocating hundreds of full-height
    # cropped images for every cut and again for every sprite in the row.
    projection = mask.resize((im.width, 1) if axis == 0 else (1, im.height),
                             Image.Resampling.BOX).tobytes()
    cross = im.height if axis == 0 else im.width
    cuts=[0]
    for i in range(1,count):
        expected=n*i/count
        scores=[]
        for p in range(round(expected-n/count*.22), round(expected+n/count*.22)):
            scores.append((projection[p]*cross/255+abs(p-expected)*.03,p))
        cuts.append(min(scores)[1])
    return cuts+[n]


def main():
    spec = json.loads((ROOT / 'tools' / 'hd-art-sources.json').read_text(encoding='utf-8'))
    OUT.mkdir(exist_ok=True)
    manifest = {}
    for sheet in spec['sheets']:
        print('Packaging '+sheet['file'], flush=True)
        path = SOURCE / sheet['file']
        if not path.exists():
            raise SystemExit(f'Missing master: {path}')
        im = Image.open(path).convert('RGBA')
        if not sheet.get('terrain') and not sheet.get('scene') and im.getchannel('A').getextrema()[0] != 0:
            raise SystemExit(f'Sprite master has no transparent background: {path}')
        cols, rows = sheet.get('grid', [4, 4])
        flat=sheet.get('terrain') or sheet.get('scene') or sheet.get('frame')
        rowcuts=[round(j*im.height/rows) for j in range(rows+1)] if flat else gutters(im,rows,1)
        columns = {}
        for i, key in enumerate(sheet['ids']):
            if not key:
                continue
            row=i//cols
            if row not in columns:
                strip=im.crop((0,rowcuts[row],im.width,rowcuts[row+1]))
                columns[row]=[round(j*im.width/cols) for j in range(cols+1)] if flat else gutters(strip,cols,0)
            cc=columns[row]
            box=[cc[i%cols],rowcuts[row],cc[i%cols+1],rowcuts[row+1]]
            part = im.crop(box)
            size = sheet.get('size', 192)
            terrain = sheet.get('terrain', False)
            if sheet.get('scene'):
                part=ImageOps.fit(part,tuple(sheet['scene']),Image.Resampling.LANCZOS)
            elif terrain or sheet.get('frame'):
                part = part.resize((size, size), Image.Resampling.LANCZOS)
            else:
                # Very low alpha halo pixels must not move an actor's baseline.
                bbox = part.getchannel('A').point(lambda a: 255 if a > 32 else 0).getbbox()
                if key.startswith('hero-worn:'):
                    bbox = subject_box(part)
                if not bbox:
                    raise SystemExit(f'Empty sprite: {key}')
                part = part.crop(bbox)
                target = round(size * sheet.get('occupancy', .90))
                part.thumbnail((target, target), Image.Resampling.LANCZOS)
                canvas = Image.new('RGBA', (size, size))
                canvas.alpha_composite(part, ((size-part.width)//2, size-round(size*.04)-part.height))
                part = canvas
            if sheet.get('brightness'):
                part = ImageEnhance.Brightness(part).enhance(sheet['brightness'])
            filename = key.replace(':', '-').replace('#', '-') + '.webp'
            part.save(OUT / filename, 'WEBP', quality=94, method=4, exact=True)
            manifest[key] = {'file': filename, 'width': part.width, 'height': part.height,
                             'source': sheet['file'], 'crop': box, 'terrain': terrain}
    for key, original in spec.get('aliases', {}).items():
        if original not in manifest:
            raise SystemExit(f'Unknown alias: {key} -> {original}')
        manifest[key] = {**manifest[original], 'aliasOf': original}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Generated asset URL table is embedded by build_single.py for offline play.
    js = 'globalThis.BABEL_HD_MANIFEST = '+json.dumps({k:v['file'] for k,v in manifest.items()}, separators=(',', ':'))+';\n'
    (ROOT / 'web' / 'hd-manifest.js').write_text(js, encoding='utf-8')
    print(f'Packaged {len(manifest)} mappings, {len(set(v["file"] for v in manifest.values()))} images')


if __name__ == '__main__':
    main()
