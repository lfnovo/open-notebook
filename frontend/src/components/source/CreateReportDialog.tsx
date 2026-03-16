import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import { Pencil, Sparkles } from "lucide-react"

interface CreateReportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const formats = [
  {
    title: "Create Your Own",
    desc: "Craft reports your way by specifying structure, style, tone, and more",
  },
  {
    title: "Briefing Doc",
    desc: "Overview of your sources featuring key insights and quotes",
  },
  {
    title: "Study Guide",
    desc: "Short-answer quiz, suggested essay questions, and glossary of key terms",
  },
  {
    title: "Blog Post",
    desc: "Insightful takeaways distilled into a highly readable article",
  },
]

const suggested = [
  {
    title: "Professional Expense Summary",
    desc: "A formal record of the job-scope subscription purchases",
  },
  {
    title: "Service Provider Profile",
    desc: "A structured overview of Remotive’s legal and contact identity",
  },
  {
    title: "Invoice Vocabulary Guide",
    desc: "An introductory document explaining the specific invoice terms",
  },
  {
    title: "Billing Structure Analysis",
    desc: "A foundational guide explaining how transaction totals are derived",
  },
]

export default function CreateReportDialog({
  open,
  onOpenChange,
}: CreateReportDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl rounded-xl p-6">
        <DialogHeader className="flex flex-row items-center gap-2">
          <Sparkles className="h-5 w-5 text-yellow-600" />
          <DialogTitle className="text-lg font-semibold">
            Create report
          </DialogTitle>
        </DialogHeader>

        <hr/>

        {/* FORMAT */}
        <div className="mt-6">
          <p className="text-lg text-muted-foreground mb-3">Format</p>

          <div className="grid grid-cols-4 gap-4">
            {formats.map((item, i) => (
              <div
                key={i}
                className="bg-[#E9E6DD] rounded-xl p-8 relative hover:shadow-sm cursor-pointer"
              >
                <h3 className="text-lg font-medium">{item.title}</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  {item.desc}
                </p>

                {i !== 0 && (
                  <div className="absolute right-3 top-3 bg-[#D9D6CC] rounded-full p-2">
                    <Pencil size={14} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* SUGGESTED */}
        <div className="mt-6">
          <p className="text-lg text-muted-foreground mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Suggested Format
          </p>

          <div className="grid grid-cols-4 gap-4">
            {suggested.map((item, i) => (
              <div
                key={i}
                className="bg-[#E9E6DD] rounded-xl p-8 relative hover:shadow-sm cursor-pointer"
              >
                <h3 className="text-lg font-medium">{item.title}</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  {item.desc}
                </p>

                <div className="absolute right-3 top-3 bg-[#D9D6CC] rounded-full p-2">
                  <Pencil size={14} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}