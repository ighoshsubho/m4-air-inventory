"""Build an evidence-labeled argument reference without inventing calling contracts."""
import collections
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def parse_signature(declaration):
    match=re.match(r'declare\s+(.+?)\s+@(air\.[\w.$-]+)\(',declaration)
    if not match: raise ValueError('Unrecognized AIR declaration')
    start=match.end(); depth=1; end=start
    while end<len(declaration) and depth:
        if declaration[end]=='(': depth+=1
        elif declaration[end]==')': depth-=1
        end+=1
    if depth: raise ValueError('Unbalanced declaration')
    text=declaration[start:end-1]; stack=[]; parts=[]; begin=0
    for i,char in enumerate(text):
        if char in '(<[{': stack.append(char)
        elif char in ')>]}':
            if not stack: raise ValueError('Unbalanced parameter type')
            stack.pop()
        elif char==',' and not stack:
            parts.append(text[begin:i].strip());begin=i+1
    if text.strip(): parts.append(text[begin:].strip())
    if stack: raise ValueError('Unbalanced parameter type')
    return {'symbol':match[2],'return_type':match[1],'parameters':parts,'declaration':declaration}


def conversion_candidate(name):
    match=re.fullmatch(r'air\.convert\.([suf])\.(v\d+)?(i\d+|f\d+|bf16)\.([suf])\.(v\d+)?(i\d+|f\d+|bf16)((?:\.[a-z]+)*)',name)
    if not match: return None
    def typ(vector,scalar):
        scalar={'f16':'half','f32':'float','f64':'double','bf16':'bfloat'}.get(scalar,scalar)
        return '<'+vector[1:]+' x '+scalar+'>' if vector else scalar
    return {'status':'name_inferred_candidate','input_type':typ(match[5],match[6]),'output_type':typ(match[2],match[3]),'input_kind':match[4],'output_kind':match[1],'qualifiers':match[7].strip('.').split('.') if match[7] else [],'candidate_value':'1 (splat to the named vector shape)','limitations':'Type/value inferred from name tokens, not a verified signature or executable example. Argument count, extra controls, feature availability and rounding/saturation contracts remain unresolved.'}


def main():
    catalog=json.loads((ROOT/'AIR-INTRINSICS.json').read_text())
    runtime=json.loads((ROOT/'GPU-RESULTS.json').read_text())['cases']
    rows={r['name']:{'name':r['name'],'versions':list(r['versions']),'signatures':[],'kernel_examples':[],'candidate':conversion_candidate(r['name']),'status':'unresolved'} for r in catalog['intrinsics']}
    overloaded={r['name']:any(v['overloaded'] for v in r['versions'].values()) for r in catalog['intrinsics']}
    names=sorted(rows,key=len,reverse=True)
    def owner(symbol):
        return next((n for n in names if symbol==n or overloaded[n] and symbol.startswith(n+'.')),None)
    def add(base,declaration,source):
        sig=parse_signature(declaration)
        existing=next((s for s in rows[base]['signatures'] if s['declaration']==declaration),None)
        if existing is None:
            sig['sources']=[source];rows[base]['signatures'].append(sig)
        elif source not in existing['sources']: existing['sources'].append(source)
    for item in catalog['intrinsics']:
        for obs in item['observations']: add(item['name'],obs['declaration'],obs['source'])
    for case in runtime:
        for declaration in case['declarations']:
            sig=parse_signature(declaration);base=owner(sig['symbol'])
            if base is None: raise ValueError('Observed symbol has no catalog base')
            add(base,declaration,case['source'])
            example={'case':case['name'],'source':case['source'],'symbol':sig['symbol'],'input_buffer_hex':case.get('input_hex'),'threads':case['threads'],'meaning':'Input to the complete source kernel, NOT positional AIR operands. See source for intermediate values, pointers and constants.'}
            if example not in rows[base]['kernel_examples']:rows[base]['kernel_examples'].append(example)
    for row in rows.values():
        row['status']='observed_signature' if row['signatures'] else 'name_inferred_candidate' if row['candidate'] else 'unresolved'
    summary=dict(collections.Counter(r['status'] for r in rows.values()))
    result={'scope':'One row per catalog base across all extracted versions; observed signatures cover specific overloads only. Name-inferred candidates are not tested call recipes. Unresolved rows deliberately omit invented operands.','summary':summary,'intrinsics':[rows[n] for n in sorted(rows)]}
    (ROOT/'AIR-ARGUMENTS.json').write_text(json.dumps(result,indent=2)+'\n')
    text=['# AIR argument reference','',result['scope'],'',
          '## Reading the table','',
          '- **Observed:** parameter order and types are copied from compiler-emitted declarations; pointer attributes and address spaces are preserved. This does not establish all valid values or all overloads.',
          '- **Candidate:** conversion source/destination types are inferred from name tokens. `1` is an exploratory value, not proof that a particular declaration, shader stage or GPU supports the call.',
          '- **Unresolved:** there is not enough evidence to specify arguments. These rows are research gaps, not callable examples.',
          '- Source links show complete kernel usage. Kernel buffer inputs are not direct AIR arguments. Opaque resources, pointer bounds/alignment, immediate constraints and synchronization must be established separately.',
          '- Exact declarations, source links and recorded kernel input bytes are retained in `AIR-ARGUMENTS.json`. Raw IIT words alone are not decoded signatures.','',
          '## All intrinsic bases','',
          '| Intrinsic | Evidence | Observed arguments → return | Potential argument / example |',
          '|---|---|---|---|']
    def esc(value):return value.replace('|','\\|').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
    for row in result['intrinsics']:
        signatures=[]
        for s in row['signatures']:
            display='('+', '.join(s['parameters'])+') → '+s['return_type']
            if display not in signatures:signatures.append(display)
        candidate=row['candidate']; examples=row['kernel_examples']
        if examples:
            example=examples[0]
            detail='[Kernel example]('+example['source']+'); '+str(example['threads'])+' thread(s). Inputs in JSON; not direct operands.'
        elif candidate:detail=esc(candidate['input_type']+' value 1 → '+candidate['output_type'])+'; name-inferred, contract unverified'
        elif row['signatures']:
            source=row['signatures'][0]['sources'][0];detail='[Compile-only source]('+source+'); valid runtime values not established'
        else:detail='Unresolved: signature, operand constraints and source route needed'
        text.append('| '+row['name']+' | '+row['status']+' | '+('<br>'.join(esc(s) for s in signatures) or 'Not established')+' | '+detail+' |')
    (ROOT/'AIR-ARGUMENTS.md').write_text('\n'.join(text)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
