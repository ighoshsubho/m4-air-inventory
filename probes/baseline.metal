#include <metal_stdlib>
using namespace metal;
kernel void baseline(device const float *input [[buffer(0)]],
                     device float *output [[buffer(1)]],
                     uint i [[thread_position_in_grid]]) {
    output[i] = sin(input[i]);
}
