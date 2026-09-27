// Local-only OCR. No windows, network requests, or source-file mutations.
import Foundation
import Vision
import PDFKit
import AppKit
import ImageIO

enum ExtractError: Error { case invalidDocument, encrypted, imageTooLarge }
func recognize(_ image: CGImage) throws -> String {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    if #available(macOS 13, *) { request.automaticallyDetectsLanguage = true }
    let supported = try request.supportedRecognitionLanguages()
    request.recognitionLanguages = ["tr-TR", "en-US"].filter { supported.contains($0) }
    try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
}
do {
    let input = FileHandle.standardInput.readDataToEndOfFile()
    if CommandLine.arguments.dropFirst().first == "pdf" {
        guard let doc = PDFDocument(data: input) else { throw ExtractError.invalidDocument }
        if doc.isLocked { throw ExtractError.encrypted }
        for i in 0..<doc.pageCount {
            let value: String = try autoreleasepool {
                guard let page = doc.page(at: i) else { throw ExtractError.invalidDocument }
                let text = page.string ?? ""
                if text.trimmingCharacters(in: .whitespacesAndNewlines).count >= 40 { return text }
                let box = page.bounds(for: .mediaBox)
                let scale = min(2.1, 2400 / max(box.width, box.height))
                let image = page.thumbnail(of: NSSize(width: max(1,box.width*scale), height: max(1,box.height*scale)), for: .mediaBox)
                guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { throw ExtractError.invalidDocument }
                let ocr = try recognize(cg)
                return ocr.isEmpty ? text : ocr
            }
            print("\n[Page \(i+1)]\n\(value)")
        }
    } else {
        guard let source = CGImageSourceCreateWithData(input as CFData, nil) else { throw ExtractError.invalidDocument }
        for i in 0..<CGImageSourceGetCount(source) {
            let value: String = try autoreleasepool {
                let options = [kCGImageSourceCreateThumbnailFromImageAlways: true, kCGImageSourceThumbnailMaxPixelSize: 3000, kCGImageSourceCreateThumbnailWithTransform: true] as CFDictionary
                guard let image = CGImageSourceCreateThumbnailAtIndex(source, i, options) else { throw ExtractError.invalidDocument }
                return try recognize(image)
            }
            print(value)
        }
    }
} catch {
    FileHandle.standardError.write(Data("ocr_failed\n".utf8)); exit(1)
}
