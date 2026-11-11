"""Merge motion-capture clips from the Ready Player Me animation library into the avatar GLB (same skeleton names), so Blender's
glTF importer builds correct actions on the avatar armature.   python3 rpmtool.py <animlib_dir> <out.glb> clip1 clip2 ..."""
import json, struct, sys, os

def read_glb(p):
    d = open(p, 'rb').read(); assert d[:4] == b'glTF'
    off = 12; js = None; bn = b''
    while off < len(d):
        ln, ty = struct.unpack('<II', d[off:off + 8]); ch = d[off + 8: off + 8 + ln]
        if ty == 0x4E4F534A: js = json.loads(ch.decode('utf8'))
        elif ty == 0x004E4942: bn = ch
        off += 8 + ln
    return js, bytearray(bn)

def write_glb(js, bn, p):
    j = json.dumps(js, separators=(',', ':')).encode('utf8'); j += b' ' * ((4 - len(j) % 4) % 4)
    bn = bytes(bn) + b'\0' * ((4 - len(bn) % 4) % 4)
    out = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(j) + 8 + len(bn)) + struct.pack('<II', len(j), 0x4E4F534A) + j + struct.pack('<II', len(bn), 0x004E4942) + bn
    open(p, 'wb').write(out)

def merge(lib, out, clips, gender='masculine'):
    base = os.path.join(lib, gender, 'glb')
    js, bn = read_glb(os.path.join(base, ('Masculine' if gender == 'masculine' else 'Feminine') + '_TPose.glb'))
    names = {n.get('name'): i for i, n in enumerate(js['nodes'])}
    js.setdefault('animations', []); js['animations'] = []
    for c in clips:
        sub = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        path = next((os.path.join(base, d, c + '.glb') for d in sub if os.path.exists(os.path.join(base, d, c + '.glb'))), None)
        if not path: print('missing', c); continue
        cj, cb = read_glb(path); cn = [n.get('name') for n in cj['nodes']]
        acc_map = {}
        def copy_acc(ai):
            if ai in acc_map: return acc_map[ai]
            a = dict(cj['accessors'][ai]); bv = cj['bufferViews'][a['bufferView']]
            data = bytes(cb[bv.get('byteOffset', 0): bv.get('byteOffset', 0) + bv['byteLength']])
            while len(bn) % 4: bn.append(0)
            o = len(bn); bn.extend(data)
            js['bufferViews'].append({'buffer': 0, 'byteOffset': o, 'byteLength': len(data)})
            a['bufferView'] = len(js['bufferViews']) - 1; a.pop('byteOffset', None) if False else None
            js['accessors'].append(a); acc_map[ai] = len(js['accessors']) - 1; return acc_map[ai]
        for an in cj.get('animations', [])[:1]:
            samplers = []; chans = []; smap = {}
            for ch in an['channels']:
                nm = cn[ch['target']['node']]
                if nm not in names: continue
                s = an['samplers'][ch['sampler']]
                if ch['sampler'] not in smap:
                    samplers.append({'input': copy_acc(s['input']), 'output': copy_acc(s['output']), 'interpolation': s.get('interpolation', 'LINEAR')}); smap[ch['sampler']] = len(samplers) - 1
                chans.append({'sampler': smap[ch['sampler']], 'target': {'node': names[nm], 'path': ch['target']['path']}})
            js['animations'].append({'name': c, 'samplers': samplers, 'channels': chans})
    js['buffers'][0]['byteLength'] = len(bn)
    write_glb(js, bn, out); print('wrote', out, len(js['animations']), 'animations', len(bn) // 1024, 'KB')

if __name__ == '__main__':
    merge(sys.argv[1], sys.argv[2], sys.argv[3:])
