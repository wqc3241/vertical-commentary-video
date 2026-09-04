// figure_tool — macOS Vision helpers for cover compositing (no ML downloads, ships with macOS 14+).
//   figure_tool cutout <in.png> <out.png>   → foreground instance mask → RGBA PNG (transparent bg)
//   figure_tool face   <in.png>             → prints "x y w h" of the largest face, top-left pixel coords
// Build: swiftc -O figure_tool.swift -o figure_tool   (cover_bust.py does this automatically)
import Vision
import CoreImage
import Foundation

func fail(_ msg: String) -> Never { FileHandle.standardError.write((msg + "\n").data(using: .utf8)!); exit(1) }

let args = CommandLine.arguments
guard args.count >= 3 else { fail("usage: figure_tool cutout <in> <out> | figure_tool face <in>") }
let mode = args[1]
let inURL = URL(fileURLWithPath: args[2])
guard let ci = CIImage(contentsOf: inURL) else { fail("ERR load \(inURL.path)") }
let handler = VNImageRequestHandler(ciImage: ci)

if mode == "face" {
  let req = VNDetectFaceRectanglesRequest()
  do { try handler.perform([req]) } catch { fail("ERR perform \(error)") }
  guard let faces = req.results, !faces.isEmpty else { fail("ERR no face") }
  // Vision boxes are normalized, origin bottom-left → convert to top-left pixel coords
  let W = ci.extent.width, H = ci.extent.height
  let best = faces.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height })!
  let b = best.boundingBox
  let x = Int((b.minX * W).rounded()), w = Int((b.width * W).rounded()), h = Int((b.height * H).rounded())
  let y = Int(((1 - b.maxY) * H).rounded())
  print("\(x) \(y) \(w) \(h)")
  exit(0)
}

guard mode == "cutout", args.count >= 4 else { fail("usage: figure_tool cutout <in> <out>") }
let outURL = URL(fileURLWithPath: args[3])
let req = VNGenerateForegroundInstanceMaskRequest()
do { try handler.perform([req]) } catch { fail("ERR perform \(error)") }
guard let result = req.results?.first else { fail("ERR no foreground instance") }
do {
  let maskPB = try result.generateScaledMaskForImage(forInstances: result.allInstances, from: handler)
  let maskCI = CIImage(cvPixelBuffer: maskPB)
  let blend = CIFilter(name: "CIBlendWithMask")!
  blend.setValue(ci, forKey: kCIInputImageKey)
  blend.setValue(CIImage(color: CIColor(red: 0, green: 0, blue: 0, alpha: 0)).cropped(to: ci.extent), forKey: kCIInputBackgroundImageKey)
  blend.setValue(maskCI, forKey: kCIInputMaskImageKey)
  guard let out = blend.outputImage else { fail("ERR blend") }
  let ctx = CIContext()
  try ctx.writePNGRepresentation(of: out, to: outURL, format: .RGBA8, colorSpace: ci.colorSpace ?? CGColorSpace(name: CGColorSpace.sRGB)!)
  print("OK instances=\(result.allInstances.count)")
} catch { fail("ERR mask \(error)") }
