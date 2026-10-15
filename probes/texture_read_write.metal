#include <metal_stdlib>
using namespace metal;
kernel void probe(texture2d<uint,access::read> src [[texture(0)]], texture2d<uint,access::write> dst [[texture(1)]], uint2 i [[thread_position_in_grid]]) { dst.write(src.read(i),i); }
