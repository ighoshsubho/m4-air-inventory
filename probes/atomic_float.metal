#include <metal_stdlib>
using namespace metal;
kernel void probe(device atomic_float *a [[buffer(0)]], device float *b [[buffer(1)]]) {
 float x=atomic_load_explicit(a,memory_order_relaxed);
 b[0]=atomic_fetch_add_explicit(a,float(1),memory_order_relaxed);
 b[1]=atomic_exchange_explicit(a,x,memory_order_relaxed);
 atomic_store_explicit(a,x,memory_order_relaxed);
 b[2]=atomic_compare_exchange_weak_explicit(a,&x,float(2),memory_order_relaxed,memory_order_relaxed);
}
