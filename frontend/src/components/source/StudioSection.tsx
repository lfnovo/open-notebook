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
} from "lucide-react"

const actions = [
  {
    title: "Audio Overview",
    icon: Brain,
    bg: "bg-[#E8F0FE] dark:bg-[#2f3442]",
    text: "text-[#1a73e8]",
    iconColor: "text-[#1a73e8]",
  },
  {
    title: "Slide deck",
    icon: Layout,
    bg: "bg-[#F3E8FF] dark:bg-[#3a2f42]",
    text: "text-[#9333ea]",
    iconColor: "text-[#9333ea]",
  },
  {
    title: "Video Overview",
    icon: Video,
    bg: "bg-[#E6F4EA] dark:bg-[#2f3f36]",
    text: "text-[#188038]",
    iconColor: "text-[#188038]",
  },
  {
    title: "Mind Map",
    icon: Brain,
    bg: "bg-[#FCE8F3] dark:bg-[#3f2f3a]",
    text: "text-[#d63384]",
    iconColor: "text-[#d63384]",
  },
  {
    title: "Reports",
    icon: BarChart3,
    bg: "bg-[#FFF4E5] dark:bg-[#3f372f]",
    text: "text-[#f59e0b]",
    iconColor: "text-[#f59e0b]",
  },
  {
    title: "Flashcards",
    icon: Layers,
    bg: "bg-[#FDECEA] dark:bg-[#3f2f2f]",
    text: "text-[#d93025]",
    iconColor: "text-[#d93025]",
  },
  {
    title: "Quiz",
    icon: HelpCircle,
    bg: "bg-[#E8F0FE] dark:bg-[#2f3442]",
    text: "text-[#1a73e8]",
    iconColor: "text-[#1a73e8]",
  },
  {
    title: "Infographic",
    icon: BarChart3,
    bg: "bg-[#F3E8FF] dark:bg-[#3a2f42]",
    text: "text-[#9333ea]",
    iconColor: "text-[#9333ea]",
  },
  {
    title: "Data table",
    icon: Table,
    bg: "bg-[#EEF2FF] dark:bg-[#2f3342]",
    text: "text-[#4f46e5]",
    iconColor: "text-[#4f46e5]",
  },
]

export function StudioActionsCard() {
  return (
    <Card className="flex flex-col flex-1 h-1/2 my-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-center text-[25px]">
          Studio
        </CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-3 gap-3">
        {actions.map((action, index) => {
          const Icon = action.icon
          return (
            <Button
              key={index}
              variant="ghost"
              className={`flex flex-col items-start gap-2 h-auto py-3 px-3 rounded-xl border-0 ${action.bg} hover:scale-[1.02] transition`}
            >
              <div className="flex items-center justify-between w-full">
                <Icon className={`h-4 w-4 ${action.iconColor}`} />
             
              </div>

              <span className={`text-xs text-left font-medium ${action.text}`}>
                {action.title}
              </span>
            </Button>
          )
        })}
      </CardContent>
    </Card>
  )
}