#include <metal_stdlib>
using namespace metal;
kernel void probe(device const char *a [[buffer(0)]],
                  device short *b [[buffer(1)]]) {
    b[0] = short(a[0]);
}
