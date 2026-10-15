#include <metal_stdlib>
using namespace metal;
kernel void probe(device atomic_uint *a [[buffer(0)]], device uint *b [[buffer(1)]]) {
 uint x=atomic_load_explicit(a,memory_order_relaxed);
 b[0]=atomic_fetch_add_explicit(a,uint(1),memory_order_relaxed);
 b[1]=atomic_exchange_explicit(a,x,memory_order_relaxed);
 atomic_store_explicit(a,x,memory_order_relaxed);
 b[2]=atomic_compare_exchange_weak_explicit(a,&x,uint(2),memory_order_relaxed,memory_order_relaxed);
}
