#include <metal_stdlib>
using namespace metal;
kernel void probe(device const float4 *a [[buffer(0)]], device float4 *b [[buffer(1)]]) {
  float4 x=a[0], y=a[1], z=a[2];
  b[0] = sin(x);
  b[1] = cos(x);
  b[2] = tan(x);
  b[3] = asin(x);
  b[4] = acos(x);
  b[5] = atan(x);
  b[6] = exp(x);
  b[7] = exp2(x);
  b[8] = log(x);
  b[9] = log2(x);
  b[10] = sqrt(x);
  b[11] = rsqrt(x);
  b[12] = floor(x);
  b[13] = ceil(x);
  b[14] = trunc(x);
  b[15] = round(x);
  b[16] = fma(x,y,z);
  b[17] = pow(x,y);
  b[18] = atan2(x,y);
  b[19] = fmod(x,y);
  b[20] = min(x,y);
  b[21] = max(x,y);
}
