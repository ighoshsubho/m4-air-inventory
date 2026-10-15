#include <metal_stdlib>
using namespace metal;

// Dispatch exactly one GPU thread.
kernel void probe(device const int *input [[buffer(0)]],
                  device int *out [[buffer(1)]]) {
    threadgroup atomic_int storage;
    threadgroup atomic_int *state = &storage;
    atomic_store_explicit(state, input[0], memory_order_relaxed);
    out[0] = atomic_load_explicit(state, memory_order_relaxed);
    atomic_store_explicit(state, 20, memory_order_relaxed);
    out[1] = atomic_load_explicit(state, memory_order_relaxed);
    out[2] = atomic_exchange_explicit(state, -30, memory_order_relaxed);
    out[3] = atomic_load_explicit(state, memory_order_relaxed);
    out[4] = atomic_fetch_add_explicit(state, 7, memory_order_relaxed);
    out[5] = atomic_load_explicit(state, memory_order_relaxed);
    out[6] = atomic_fetch_sub_explicit(state, 5, memory_order_relaxed);
    out[7] = atomic_load_explicit(state, memory_order_relaxed);
    out[8] = atomic_fetch_min_explicit(state, -40, memory_order_relaxed);
    out[9] = atomic_load_explicit(state, memory_order_relaxed);
    out[10] = atomic_fetch_max_explicit(state, 24, memory_order_relaxed);
    out[11] = atomic_load_explicit(state, memory_order_relaxed);
    out[12] = atomic_fetch_and_explicit(state, 15, memory_order_relaxed);
    out[13] = atomic_load_explicit(state, memory_order_relaxed);
    out[14] = atomic_fetch_or_explicit(state, 3, memory_order_relaxed);
    out[15] = atomic_load_explicit(state, memory_order_relaxed);
    out[16] = atomic_fetch_xor_explicit(state, 6, memory_order_relaxed);
    out[17] = atomic_load_explicit(state, memory_order_relaxed);
    // State is 13, so expected=99 cannot match, even for weak CAS.
    int expected = 99;
    out[18] = int(atomic_compare_exchange_weak_explicit(state, &expected, 77, memory_order_relaxed, memory_order_relaxed));
    out[19] = expected;
    out[20] = atomic_load_explicit(state, memory_order_relaxed);
}
