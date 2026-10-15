#include <metal_stdlib>
using namespace metal;
kernel void probe(device const uchar *a [[buffer(0)]],
                  device ushort *b [[buffer(1)]]) {
    b[0] = ushort(a[0]);
}
