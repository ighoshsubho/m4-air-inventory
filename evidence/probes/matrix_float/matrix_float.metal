#include <metal_stdlib>
using namespace metal;
kernel void probe(device const float4x4 *a [[buffer(0)]], device float4x4 *b [[buffer(1)]], device float *c [[buffer(2)]]) { b[0]=a[0]*a[1]; b[1]=transpose(a[0]); c[0]=determinant(a[0]); }
