#include <metal_stdlib>
using namespace metal;
kernel void probe(device const int *a [[buffer(0)]], device int *b [[buffer(1)]]) {
  int x=a[0], y=a[1];
  b[0] = clz(x);
  b[1] = ctz(x);
  b[2] = popcount(x);
  b[3] = reverse_bits(x);
  b[4] = mulhi(x,y);
  b[5] = addsat(x,y);
  b[6] = subsat(x,y);
  b[7] = rotate(x,y);
  b[8] = min(x,y);
  b[9] = max(x,y);
}
