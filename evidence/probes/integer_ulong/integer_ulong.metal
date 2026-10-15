#include <metal_stdlib>
using namespace metal;
kernel void probe(device const ulong *a [[buffer(0)]], device ulong *b [[buffer(1)]]) {
  ulong x=a[0], y=a[1];
  b[0] = clz(x);
  b[1] = ctz(x);
  b[2] = popcount(x);
  b[3] = reverse_bits(x);
  b[4] = mulhi(x,y);
  b[5] = add_sat(x,y);
  b[6] = sub_sat(x,y);
  b[7] = rotate(x,y);
  b[8] = min(x,y);
  b[9] = max(x,y);
}
