// 'use client'

// import { useRouter, useParams } from 'next/navigation'
// import { useCallback } from 'react'
// import { Button } from '@/components/ui/button'
// import { ArrowLeft } from 'lucide-react'
// import { useSourceChat } from '@/lib/hooks/useSourceChat'
// import { ChatPanel } from '@/components/source/ChatPanel'
// import { useNavigation } from '@/lib/hooks/use-navigation'
// import { SourceDetailContent } from '@/components/source/SourceDetailContent'

// export default function SourceDetailPage() {
//   const router = useRouter()
//   const params = useParams()
//   const sourceId = params?.id ? decodeURIComponent(params.id as string) : ''
//   const navigation = useNavigation()

//   const chat = useSourceChat(sourceId)

//   const handleBack = useCallback(() => {
//     const returnPath = navigation.getReturnPath()
//     router.push(returnPath)
//     navigation.clearReturnTo()
//   }, [navigation, router])

//   return (
//     <div className="flex flex-col h-screen overflow-hidden">
//       {/* Back button — fixed height */}
//       <div className="flex-shrink-0 pt-4 pb-2 px-6">
//         <Button variant="ghost" size="sm" onClick={handleBack}>
//           <ArrowLeft className="mr-2 h-4 w-4" />
//           {navigation.getReturnLabel()}
//         </Button>
//       </div>

//       {/* Two-column layout — fills remaining height */}
//       <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-4 px-6 pb-4 overflow-hidden">

//         {/* Left — Source detail, scrolls independently */}
//         <div className="min-h-0 min-w-0 overflow-y-auto overflow-x-hidden pr-2">
//           <SourceDetailContent
//             sourceId={sourceId}
//             showChatButton={false}
//             onClose={handleBack}
//           />
//         </div>

//         {/* Right — Chat panel, fills height with sticky input */}
//         <div className="min-h-0 min-w-0 flex flex-col overflow-hidden">

//           {/* 🔧 Configure Chat Header */}
//           <div className="flex justify-between items-center p-2 border-b">
//             <h3 className="text-sm font-semibold">Chat</h3>

//             <button
//               className="px-3 py-1 text-xs bg-black text-white rounded"
//               onClick={() => setShowConfig(true)}
//             >
//               Configure
//             </button>
//           </div>
//           <ChatPanel
//             messages={chat.messages}
//             isStreaming={chat.isStreaming}
//             contextIndicators={chat.contextIndicators}
//             onSendMessage={(message, model) => chat.sendMessage(message, model)}
//             modelOverride={chat.currentSession?.model_override}
//             onModelChange={(model) => {
//               if (chat.currentSessionId) {
//                 chat.updateSession(chat.currentSessionId, { model_override: model })
//               }
//             }}
//             sessions={chat.sessions}
//             currentSessionId={chat.currentSessionId}
//             onCreateSession={(title) => chat.createSession({ title })}
//             onSelectSession={chat.switchSession}
//             onUpdateSession={(sessionId, title) => chat.updateSession(sessionId, { title })}
//             onDeleteSession={chat.deleteSession}
//             loadingSessions={chat.loadingSessions}
//             suggestedQuestions={chat.suggestedQuestions}
//           />
//         </div>
//       </div>
//     </div>
//   )
// }




'use client'

import { useRouter, useParams } from 'next/navigation'
import { useCallback, useState } from 'react' // Added useState
import { Button } from '@/components/ui/button'
import { ArrowLeft, Settings2 } from 'lucide-react' // Added icon
import { useSourceChat } from '@/lib/hooks/useSourceChat'
import { ChatPanel } from '@/components/source/ChatPanel'
import { useNavigation } from '@/lib/hooks/use-navigation'
import { SourceDetailContent } from '@/components/source/SourceDetailContent'
import { ConfigureChatModal } from '@/components/source/ConfigureChatModal' // Import the new modal component

export default function SourceDetailPage() {
  const router = useRouter()
  const params = useParams()
  const sourceId = params?.id ? decodeURIComponent(params.id as string) : ''
  const navigation = useNavigation()

  // --- State for Modal and Config ---
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [chatConfig, setChatConfig] = useState({
    goal: 'Default',
    length: 'Default'
  })

  const chat = useSourceChat(sourceId)

  const handleBack = useCallback(() => {
    const returnPath = navigation.getReturnPath()
    router.push(returnPath)
    navigation.clearReturnTo()
  }, [navigation, router])

  // Custom send message that injects configuration
  const handleSendMessageWithConfig = (message: string, model?: string) => {
    const configContext = `[Style: ${chatConfig.goal}, Length: ${chatConfig.length}] `

    const cleanMessage = message.replace(configContext, '')

    chat.sendMessage(cleanMessage, model)
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Back button */}
      <div className="flex-shrink-0 pt-4 pb-2 px-6">
        <Button variant="ghost" size="sm" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {navigation.getReturnLabel()}
        </Button>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-4 px-6 pb-4 overflow-hidden">
        <div className="min-h-0 min-w-0 overflow-y-auto overflow-x-hidden pr-2">
          <SourceDetailContent sourceId={sourceId} showChatButton={false} onClose={handleBack} />
        </div>

        <div className="min-h-0 min-w-0 flex flex-col border rounded-xl bg-white overflow-hidden">
          {/* 🔧 Styled Header with "Tune" Icon */}
          <div className="flex justify-between items-center p-3 border-b bg-gray-50">
            <h3 className="text-sm font-semibold text-gray-700">Chat</h3>
            <button 
              onClick={() => setIsConfigOpen(true)}
              className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              title="Configure notebook"
            >
              <Settings2 className="h-5 w-5 text-gray-600" /> 
            </button>
          </div>

          <ChatPanel
            messages={chat.messages}
            isStreaming={chat.isStreaming}
            contextIndicators={chat.contextIndicators}
            onSendMessage={handleSendMessageWithConfig} // Use updated handler
            // ... rest of your props
            sessions={chat.sessions}
            currentSessionId={chat.currentSessionId}
            onCreateSession={(title) => chat.createSession({ title })}
            onSelectSession={chat.switchSession}
            onUpdateSession={(sessionId, title) => chat.updateSession(sessionId, { title })}
            onDeleteSession={chat.deleteSession}
            loadingSessions={chat.loadingSessions}
            suggestedQuestions={chat.suggestedQuestions}
          />
        </div>
      </div>

      {/* Configuration Modal */}
      {isConfigOpen && (
        <ConfigureChatModal 
          currentConfig={chatConfig}
          onSave={(newConfig) => {
            setChatConfig(newConfig)
            setIsConfigOpen(false)
          }}
          onClose={() => setIsConfigOpen(false)}
        />
      )}
    </div>
  )
}
