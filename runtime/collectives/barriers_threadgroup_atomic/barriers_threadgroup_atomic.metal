#include <metal_stdlib>
using namespace metal;
kernel void probe(device uint *b [[buffer(0)]], uint i [[thread_index_in_threadgroup]]) {
 threadgroup atomic_uint a;
 if(i==0) atomic_store_explicit(&a,0u,memory_order_relaxed);
 threadgroup_barrier(mem_flags::mem_threadgroup);
 uint x=atomic_fetch_add_explicit(&a,1u,memory_order_relaxed);
 simdgroup_barrier(mem_flags::mem_threadgroup);
 b[i]=x;
 threadgroup_barrier(mem_flags::mem_device);
}
