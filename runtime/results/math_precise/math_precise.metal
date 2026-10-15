#include <metal_stdlib>
using namespace metal;
#pragma clang fp contract(off)
kernel void probe(device const float *a [[buffer(0)]], device float *b [[buffer(1)]]) {
  float x=a[0];
  b[0]=precise::sin(x); b[1]=precise::cos(x); b[2]=precise::exp(x); b[3]=precise::log(x); b[4]=precise::sqrt(x); b[5]=precise::rsqrt(x);
}
