#include <metal_stdlib>
using namespace metal;
kernel void probe(device const char *a [[buffer(0)]],
                  device char *b [[buffer(1)]]) {
    b[0] = char(a[0]);
}
