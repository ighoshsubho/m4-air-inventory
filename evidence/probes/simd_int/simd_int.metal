#include <metal_stdlib>
using namespace metal;
kernel void probe(device const int *a [[buffer(0)]], device int *b [[buffer(1)]], uint i [[thread_position_in_grid]]) {
  int x=a[i];
  b[i*8]=simd_sum(x); b[i*8+1]=simd_min(x); b[i*8+2]=simd_max(x);
  b[i*8+3]=simd_shuffle(x,ushort(0)); b[i*8+4]=simd_shuffle_xor(x,ushort(1));
  b[i*8+5]=simd_prefix_exclusive_sum(x); b[i*8+6]=simd_prefix_inclusive_sum(x); b[i*8+7]=quad_shuffle(x,ushort(0));
}
