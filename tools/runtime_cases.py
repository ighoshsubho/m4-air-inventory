"""Small, reviewed buffer layouts and CPU reference outputs; no generated IR."""
import math
import struct


def math_case(name, fmt, lanes):
    x, y, z = 0.25, 0.5, 0.75
    expected = [math.sin(x), math.cos(x), math.tan(x), math.asin(x), math.acos(x), math.atan(x), math.exp(x), 2**x, math.log(x), math.log2(x), math.sqrt(x), 1/math.sqrt(x), math.floor(x), math.ceil(x), math.trunc(x), 0, x*y+z, x**y, math.atan2(x,y), math.fmod(x,y), min(x,y), max(x,y)]
    return {'name':name, 'format':fmt, 'threads':1, 'input':struct.pack('<'+fmt*(3*lanes), *([x]*lanes+[y]*lanes+[z]*lanes)), 'expected':[v for value in expected for v in [value]*lanes], 'tolerance':0.004 if fmt=='e' else 0.00005, 'flags':[]}


def integer_case(name, bits, signed, lanes):
    x, y = 24, 3
    mask = (1 << bits)-1
    convert = lambda value: value-(1<<bits) if signed and value >= (1<<(bits-1)) else value
    reverse = convert(int(format(x, '0'+str(bits)+'b')[::-1],2))
    expected = [bits-x.bit_length(), (x & -x).bit_length()-1, bin(x).count('1'), reverse, 0, x+y, x-y, convert(((x<<y)|(x>>(bits-y)))&mask), min(x,y), max(x,y)]
    fmt = {(16,True):'h',(16,False):'H',(32,True):'i',(32,False):'I',(64,True):'q',(64,False):'Q'}[bits,signed]
    return {'name':name, 'format':fmt, 'threads':1, 'input':struct.pack('<'+fmt*(2*lanes), *([x]*lanes+[y]*lanes)), 'expected':[v for value in expected for v in [value]*lanes], 'tolerance':0, 'flags':[]}


def all_cases():
    cases = [math_case('math_'+name,fmt,lanes) for name,fmt,lanes in [('float','f',1),('half','e',1),('float2','f',2),('half2','e',2),('float4','f',4),('half4','e',4)]]
    precise = math_case('math_precise','f',1)
    precise.update(expected=[math.sin(0.25),math.cos(0.25),math.exp(0.25),math.log(0.25),math.sqrt(0.25),2.0], flags=['-fno-fast-math'])
    cases.append(precise)
    cases += [integer_case('integer_'+name,bits,signed,lanes) for name,bits,signed,lanes in [('int',32,True,1),('uint',32,False,1),('short4',16,True,4),('ushort4',16,False,4),('long',64,True,1),('ulong',64,False,1)]]
    for name,fmt in [('float','f'),('half','e'),('int','i'),('uint','I')]:
        expected=[v for i in range(32) for v in [32,1,1,1,1,i,i+1,1]]
        cases.append({'name':'simd_'+name,'format':fmt,'threads':32,'required_width':32,'input':struct.pack('<'+fmt*32,*([1]*32)), 'expected':expected,'tolerance':0,'flags':[]})
    cases.append({'name':'barriers_threadgroup_atomic','format':'I','threads':32,'required_width':32,'input':b'', 'expected':list(range(32)),'tolerance':0,'flags':[],'output_binding':0,'unordered':True})
    cases.append({'name':'simd_vote','format':'Q','threads':32,'required_width':32,'input':struct.pack('<32i',*([1]*32)), 'expected':[v for _ in range(32) for v in (1,1,(1<<32)-1)],'tolerance':0,'flags':[]})
    identity=[float(i%9==0) for i in range(64)]
    for name,fmt in [('float','f'),('half','e')]:
        cases.append({'name':'simd_matrix_'+name,'format':fmt,'threads':32,'required_width':32,'input':struct.pack('<'+fmt*192,*(identity+identity+[0.0]*64)),'expected':identity,'tolerance':0,'flags':[]})
    return cases
