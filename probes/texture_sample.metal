#include <metal_stdlib>
using namespace metal;
kernel void probe(texture2d<float> t [[texture(0)]], sampler s [[sampler(0)]], device const float2 *uv [[buffer(0)]], device float4 *b [[buffer(1)]]) {
 b[0]=t.sample(s,uv[0],level(0)); b[1]=t.gather(s,uv[0]); b[2]=float4(t.get_width(),t.get_height(),t.get_num_mip_levels(),0);
}
