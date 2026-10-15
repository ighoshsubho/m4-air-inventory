#include <metal_stdlib>
using namespace metal;
kernel void probe(depth2d<float> t [[texture(0)]], sampler s [[sampler(0)]], device const float3 *uv [[buffer(0)]], device float *b [[buffer(1)]]) { b[0]=t.sample_compare(s,uv[0].xy,uv[0].z,level(0)); }
