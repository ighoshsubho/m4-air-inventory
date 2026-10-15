#include <metal_stdlib>
using namespace metal;
#include <metal_raytracing>
using namespace metal::raytracing;
kernel void probe(primitive_acceleration_structure scene [[buffer(0)]], device const float3 *a [[buffer(1)]], device float *b [[buffer(2)]]) {
 ray r(a[0],a[1],0.0f,1000.0f); intersector<triangle_data> query; auto hit=query.intersect(r,scene); b[0]=hit.distance; b[1]=float(hit.type);
}
