#include <metal_stdlib>
using namespace metal;
kernel void probe(device const half *a [[buffer(0)]], device half *b [[buffer(1)]]) {
  half x=a[0];
  b[0]=acosh(x+half(1));
  b[1]=asinh(x);
  b[2]=atanh(x);
  b[3]=cosh(x);
  b[4]=sinh(x);
  b[5]=tanh(x);
  b[6]=exp10(x);
  b[7]=log10(x);
  b[8]=rint(x);
  b[9]=fract(x);
  b[10]=powr(x,half(2));
  b[11]=fabs(-x);
  b[12]=copysign(x,-x);
  b[13]=fdim(x,half(1));
}
