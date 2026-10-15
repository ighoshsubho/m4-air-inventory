#include <metal_stdlib>
using namespace metal;

// Dispatch exactly one GPU thread.
kernel void probe(device atomic_float *state [[buffer(0)]],
                  device float *out [[buffer(1)]]) {
    out[0] = atomic_load_explicit(state, memory_order_relaxed);
    atomic_store_explicit(state, 2.5f, memory_order_relaxed);
    out[1] = atomic_load_explicit(state, memory_order_relaxed);
    out[2] = atomic_exchange_explicit(state, 4.0f, memory_order_relaxed);
    out[3] = atomic_load_explicit(state, memory_order_relaxed);
    out[4] = atomic_fetch_add_explicit(state, 0.5f, memory_order_relaxed);
    out[5] = atomic_load_explicit(state, memory_order_relaxed);
    out[6] = atomic_fetch_sub_explicit(state, 1.0f, memory_order_relaxed);
    out[7] = atomic_load_explicit(state, memory_order_relaxed);
    // State is 3.5, so expected=99 cannot match, even for weak CAS.
    float expected = 99.0f;
    out[8] = float(atomic_compare_exchange_weak_explicit(state, &expected, 77.0f, memory_order_relaxed, memory_order_relaxed));
    out[9] = expected;
    out[10] = atomic_load_explicit(state, memory_order_relaxed);
}
