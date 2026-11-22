import Foundation
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
import AppKit

let args = CommandLine.arguments
let entrada = URL(fileURLWithPath: args[1]), salida = URL(fileURLWithPath: args[2])
let imagen = CIImage(contentsOf: entrada)!
let solicitud = VNGenerateForegroundInstanceMaskRequest()
let manejador = VNImageRequestHandler(ciImage: imagen)
try manejador.perform([solicitud])
guard let resultado = solicitud.results?.first else { print("sin resultado"); exit(1) }
print("instancias:", resultado.allInstances.count)
let mascara = try resultado.generateScaledMaskForImage(forInstances: resultado.allInstances, from: manejador)
let ciMascara = CIImage(cvPixelBuffer: mascara)
let contexto = CIContext()
let cg = contexto.createCGImage(ciMascara, from: ciMascara.extent)!
let rep = NSBitmapImageRep(cgImage: cg)
try rep.representation(using: .png, properties: [:])!.write(to: salida)
print("ok", ciMascara.extent)
