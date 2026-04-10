import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Brain,
  Video,
  Layout,
  BarChart3,
  Layers,
  HelpCircle,
  Table,
  GitBranch,
  Newspaper,
} from "lucide-react"

import CreateReportDialog from "./CreateReportDialog"
import { MindMapDialog } from "./MindMapDialog"
import { InfographicDialog } from "./InfographicDialog"
import { useState } from "react"

const actions = [
  // {
  //   title: "Audio Overview",
  //   icon: Brain,
  //   bg: "bg-[#E8F0FE] dark:bg-[#2f3442]",
  //   text: "text-[#1a73e8]",
  //   iconColor: "text-[#1a73e8]",
  // },
  // {
  //   title: "Slide deck",
  //   icon: Layout,
  //   bg: "bg-[#F3E8FF] dark:bg-[#3a2f42]",
  //   text: "text-[#9333ea]",
  //   iconColor: "text-[#9333ea]",
  // },
  // {
  //   title: "Video Overview",
  //   icon: Video,
  //   bg: "bg-[#E6F4EA] dark:bg-[#2f3f36]",
  //   text: "text-[#188038]",
  //   iconColor: "text-[#188038]",
  // },
  {
    title: "Mind Map",
    icon: GitBranch,
    bg: "bg-[#FCE8F3] dark:bg-[#3f2f3a]",
    text: "text-[#d63384]",
    iconColor: "text-[#d63384]",
  },
  // {
  //   title: "Reports",
  //   icon: BarChart3,
  //   bg: "bg-[#FFF4E5] dark:bg-[#3f372f]",
  //   text: "text-[#f59e0b]",
  //   iconColor: "text-[#f59e0b]",
  // },
  // {
  //   title: "Flashcards",
  //   icon: Layers,
  //   bg: "bg-[#FDECEA] dark:bg-[#3f2f2f]",
  //   text: "text-[#d93025]",
  //   iconColor: "text-[#d93025]",
  // },
  // {
  //   title: "Quiz",
  //   icon: HelpCircle,
  //   bg: "bg-[#E8F0FE] dark:bg-[#2f3442]",
  //   text: "text-[#1a73e8]",
  //   iconColor: "text-[#1a73e8]",
  // },
  {
    title: "Infographic",
    icon: Newspaper,
    bg: "bg-[#F3E8FF] dark:bg-[#3a2f42]",
    text: "text-[#9333ea]",
    iconColor: "text-[#9333ea]",
  },
  // {
  //   title: "Data table",
  //   icon: Table,
  //   bg: "bg-[#EEF2FF] dark:bg-[#2f3342]",
  //   text: "text-[#4f46e5]",
  //   iconColor: "text-[#4f46e5]",
  // },
]

interface StudioActionsCardProps {
  sourceId?: string
  sourceTitle?: string | null
}

export function StudioActionsCard({ sourceId, sourceTitle }: StudioActionsCardProps) {
  const [reportOpen, setReportOpen] = useState(false)
  const [mindMapOpen, setMindMapOpen] = useState(false)
  const [infographicOpen, setInfographicOpen] = useState(false)

  return (
    <>
      <Card className="flex flex-col flex-1 h-59">
        <CardHeader className="pb-1">
          <CardTitle className="text-center text-[25px]">Studio</CardTitle>
        </CardHeader>

        <CardContent className="flex flex-row justify-center gap-4 px-6 pb-6">
          {actions.map((action, index) => {
            const Icon = action.icon
            return (
              <Button
                key={index}
                variant="ghost"
                onClick={() => {
                  if (action.title === "Reports") setReportOpen(true)
                  else if (action.title === "Mind Map" && sourceId) setMindMapOpen(true)
                  else if (action.title === "Infographic" && sourceId) setInfographicOpen(true)
                }}
                className={`flex flex-col items-center justify-center gap-3 h-28 w-40 rounded-2xl border-0 ${action.bg} hover:scale-[1.02] transition`}
              >
                <Icon className={`h-8 w-8 ${action.iconColor}`} />
                <span className={`text-sm text-center font-medium leading-tight ${action.text}`}>
                  {action.title}
                </span>
              </Button>
            )
          })}
        </CardContent>
      </Card>

      <CreateReportDialog open={reportOpen} onOpenChange={setReportOpen} />

      {sourceId && (
        <>
          <MindMapDialog
            sourceId={sourceId}
            sourceTitle={sourceTitle}
            open={mindMapOpen}
            onOpenChange={setMindMapOpen}
          />
          <InfographicDialog
            sourceId={sourceId}
            sourceTitle={sourceTitle}
            open={infographicOpen}
            onOpenChange={setInfographicOpen}
          />
        </>
      )}
    </>
  )
}
