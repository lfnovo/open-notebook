"use client"

import { useState } from "react"
import { useDropzone } from "react-dropzone"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { UploadCloud, File as FileIcon, X } from "lucide-react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { ScrollArea } from "@/components/ui/scroll-area"

interface BatchUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  notebookId?: string
}

export function BatchUploadDialog({
  open,
  onOpenChange,
  onSuccess,
  notebookId,
}: BatchUploadDialogProps) {
  const [files, setFiles] = useState<File[]>([])

  const onDrop = (acceptedFiles: File[]) => {
    setFiles((prevFiles) => [...prevFiles, ...acceptedFiles])
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        ".docx",
      ],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
      "application/epub+zip": [".epub"],
    },
  })

  const removeFile = (file: File) => {
    setFiles((prevFiles) => prevFiles.filter((f) => f !== file))
  }

  const { mutate: uploadFiles, isPending } = useMutation({
    mutationFn: async (filesToUpload: File[]) => {
      const formData = new FormData()
      filesToUpload.forEach((file) => {
        formData.append("files", file)
      })
      if (notebookId) {
        formData.append("notebooks", JSON.stringify([notebookId]))
      }
      // This is a placeholder for the API call.
      // I will replace this with a proper API call using axios or fetch.
      const response = await fetch("/api/sources/batch", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Batch upload failed")
      }

      return response.json()
    },
    onSuccess: () => {
      toast.success("Batch upload started successfully.")
      setFiles([])
      onSuccess()
      onOpenChange(false)
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })

  const handleUpload = () => {
    if (files.length > 0) {
      uploadFiles(files)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>Batch Upload Files</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div
            {...getRootProps()}
            className={`flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted ${
              isDragActive ? "border-primary bg-muted" : "border-input"
            }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <UploadCloud className="w-10 h-10 mb-3 text-muted-foreground" />
              <p className="mb-2 text-sm text-muted-foreground">
                <span className="font-semibold">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-muted-foreground">
                PDF, DOC, DOCX, TXT, MD, EPUB
              </p>
            </div>
          </div>
          {files.length > 0 && (
            <ScrollArea className="h-40 w-full rounded-md border">
              <div className="p-4">
                <h4 className="mb-4 text-sm font-medium leading-none">
                  Selected Files
                </h4>
                {files.map((file, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-2 rounded-md hover:bg-muted"
                  >
                    <div className="flex items-center gap-2">
                      <FileIcon className="h-4 w-4" />
                      <span className="text-sm">{file.name}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeFile(file)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
        <DialogFooter>
          <Button
            onClick={handleUpload}
            disabled={files.length === 0 || isPending}
          >
            {isPending ? "Uploading..." : `Upload ${files.length} file(s)`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
