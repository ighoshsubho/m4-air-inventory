#include <metal_stdlib>
using namespace metal;
kernel void probe(device const float3 *a [[buffer(0)]], device float3 *b [[buffer(1)]], device float *c [[buffer(2)]]) {
 b[0]=normalize(a[0]); b[1]=cross(a[0],a[1]); b[2]=reflect(a[0],a[1]); b[3]=refract(a[0],a[1],0.5f); c[0]=dot(a[0],a[1]); c[1]=length(a[0]); c[2]=distance(a[0],a[1]);
}
