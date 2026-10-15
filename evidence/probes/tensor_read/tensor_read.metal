#include <metal_stdlib>
using namespace metal;
#include <metal_tensor>
kernel void probe(tensor<float,extents<int,dynamic_extent,dynamic_extent>> t [[buffer(0)]], device float *b [[buffer(1)]], uint2 i [[thread_position_in_grid]]) { b[0]=t.get(i.x,i.y); b[1]=float(t.get_extent(0)); }
