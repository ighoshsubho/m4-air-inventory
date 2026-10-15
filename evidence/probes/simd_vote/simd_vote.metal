#include <metal_stdlib>
using namespace metal;
kernel void probe(device const int *a [[buffer(0)]], device ulong *b [[buffer(1)]], uint i [[thread_position_in_grid]]) {
 bool x=a[i]!=0; b[i*3]=simd_all(x); b[i*3+1]=simd_any(x); b[i*3+2]=simd_ballot(x).get_mask();
}
