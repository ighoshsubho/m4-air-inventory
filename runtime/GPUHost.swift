import Foundation
import Metal

struct BufferSpec: Decodable {
    let index: Int
    let input: String?
    let size: Int?
    let output: String?
}
struct Spec: Decodable {
    let library: String
    let function: String
    let threads: Int
    let requiredWidth: Int?
    let buffers: [BufferSpec]
}
enum Failure: Error { case invalid(String) }
func require(_ condition: Bool, _ message: String) throws {
    if !condition { throw Failure.invalid(message) }
}

func run() throws {
    try require(CommandLine.arguments.count == 2, "Expected one trusted specification path")
    let spec = try JSONDecoder().decode(Spec.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
    try require((1...64).contains(spec.threads), "Dispatch exceeds 64-thread bound")
    try require((1...8).contains(spec.buffers.count), "Invalid buffer count")
    try require(Set(spec.buffers.map { $0.index }).count == spec.buffers.count, "Duplicate bindings")
    try require(ProcessInfo.processInfo.thermalState == .nominal, "Thermal state is not nominal")
    guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else {
        throw Failure.invalid("No Metal device or command queue")
    }
    let library = try device.makeLibrary(URL: URL(fileURLWithPath: spec.library))
    guard let function = library.makeFunction(name: spec.function) else { throw Failure.invalid("Missing function") }
    let pipeline = try device.makeComputePipelineState(function: function)
    if let width = spec.requiredWidth {
        try require(pipeline.threadExecutionWidth == width, "Collective test requires verified SIMD width")
    }
    try require(spec.threads <= pipeline.maxTotalThreadsPerThreadgroup, "Threadgroup limit exceeded")
    var bound: [(BufferSpec, MTLBuffer)] = []
    for entry in spec.buffers {
        try require((0...7).contains(entry.index), "Invalid binding")
        let data: Data?
        if let input = entry.input {
            let attributes = try FileManager.default.attributesOfItem(atPath: input)
            let length = (attributes[.size] as? NSNumber)?.intValue ?? 0
            try require((1...65536).contains(length), "Input exceeds 64 KiB bound")
            data = try Data(contentsOf: URL(fileURLWithPath: input))
        } else { data = nil }
        let size = data?.count ?? entry.size ?? 0
        try require((1...65536).contains(size), "Buffer exceeds 64 KiB bound")
        guard let buffer = device.makeBuffer(length: size, options: .storageModeShared) else {
            throw Failure.invalid("Buffer allocation failed")
        }
        memset(buffer.contents(), 0xa5, size)
        if let data = data { data.copyBytes(to: buffer.contents().assumingMemoryBound(to: UInt8.self), count: data.count) }
        bound.append((entry, buffer))
    }
    guard let command = queue.makeCommandBuffer(), let encoder = command.makeComputeCommandEncoder() else {
        throw Failure.invalid("Command creation failed")
    }
    encoder.setComputePipelineState(pipeline)
    for (entry, buffer) in bound { encoder.setBuffer(buffer, offset: 0, index: entry.index) }
    encoder.dispatchThreadgroups(MTLSize(width: 1, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: spec.threads, height: 1, depth: 1))
    encoder.endEncoding()
    let started = ProcessInfo.processInfo.systemUptime
    command.commit()
    command.waitUntilCompleted()
    try require(command.status == .completed, "GPU command failed: \(String(describing: command.error))")
    for (entry, buffer) in bound {
        if let output = entry.output {
            try Data(bytes: buffer.contents(), count: buffer.length).write(to: URL(fileURLWithPath: output))
        }
    }
    let result: [String: Any] = ["status": "completed", "device": device.name,
        "dispatch_threads": spec.threads, "thread_execution_width": pipeline.threadExecutionWidth,
        "host_elapsed_seconds": ProcessInfo.processInfo.systemUptime - started,
        "gpu_elapsed_seconds": command.gpuEndTime - command.gpuStartTime,
        "thermal_state_after": ProcessInfo.processInfo.thermalState.rawValue]
    let output = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(decoding: output, as: UTF8.self))
}

do { try run() }
catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
