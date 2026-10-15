"""Public Metal math operations, safe finite inputs, CPU libm references."""
from pathlib import Path
import math
import struct
ROOT=Path(__file__).resolve().parents[1]

def all_cases():
    rows=[]
    for scalar,fmt in [('float','f'),('half','e')]:
        for lanes in (1,2,4):
            typ=scalar+(str(lanes) if lanes>1 else '')
            xs=[0.125,0.25,0.375,0.5][:lanes]
            expressions=[('acosh(x+'+typ+'(1))',lambda x:math.acosh(x+1)),('asinh(x)',math.asinh),('atanh(x)',math.atanh),('cosh(x)',math.cosh),('sinh(x)',math.sinh),('tanh(x)',math.tanh),('exp10(x)',lambda x:10**x),('log10(x)',math.log10),('rint(x)',lambda x:0.0),('fract(x)',lambda x:x),('powr(x,'+typ+'(2))',lambda x:x*x),('fabs(-x)',lambda x:x),('copysign(x,-x)',lambda x:-x),('fdim(x,'+typ+'(1))',lambda x:0.0)]
            for precise in (False,True):
                name='extended_'+typ+('_precise' if precise else '_fast')
                path=ROOT/'runtime/math-sources'/(name+'.metal')
                path.parent.mkdir(parents=True,exist_ok=True)
                lines=['#include <metal_stdlib>','using namespace metal;',f'kernel void probe(device const {typ} *a [[buffer(0)]], device {typ} *b [[buffer(1)]]) {{',f'  {typ} x=a[0];']
                lines += [f'  b[{i}]={expr};' for i,(expr,_) in enumerate(expressions)]
                lines.append('}')
                text='\n'.join(lines)+'\n'
                if path.exists() and path.read_text()!=text: raise ValueError('Existing generated source differs')
                if not path.exists(): path.write_text(text)
                rows.append({'name':name,'source':str(path.relative_to(ROOT)),'format':fmt,'threads':1,'input':struct.pack('<'+fmt*lanes,*xs),'expected':[f(x) for _,f in expressions for x in xs],'tolerance':0.008 if fmt=='e' else 0.0001,'flags':['-fno-fast-math'] if precise else []})
    return rows
