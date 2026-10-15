#include <metal_stdlib>
using namespace metal;
kernel void probe(texture3d<half> t [[texture(0)]], sampler s [[sampler(0)]], device const float3 *uv [[buffer(0)]], device half4 *b [[buffer(1)]]) { b[0]=t.sample(s,uv[0],level(0)); }
