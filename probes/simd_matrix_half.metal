#include <metal_stdlib>
using namespace metal;
#include <metal_simdgroup_matrix>
kernel void probe(device const half *a [[buffer(0)]], device half *b [[buffer(1)]]) {
 simdgroup_matrix<half,8,8> x,y,z,r; simdgroup_load(x,a); simdgroup_load(y,a+64); simdgroup_load(z,a+128); simdgroup_multiply_accumulate(r,x,y,z); simdgroup_store(r,b);
}
