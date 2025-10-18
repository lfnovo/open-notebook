# Bug: Notebook Chat Context Not Being Sent to API

## Bug Description
The notebook chat functionality in the React frontend is failing to send proper context to the LLM. When users toggle sources/notes to include them in chat context (shown by blue icons and "1 full" indicator), the AI agent does not recognize the context and responds as if no context was provided. The context selection UI works correctly (showing selections), but the actual content is not being passed to the API endpoint.

**Symptoms:**
- Context toggle UI shows correct selections (blue icons)
- Context indicator displays "1 full" or similar status
- AI agent responds without knowledge of the selected context
- No errors in console or API logs

**Expected Behavior:**
- Selected sources/notes should be sent to the API with their actual content
- API should use "insights" or "full content" from the sources/notes based on selection mode
- AI agent should have access to the context and respond accordingly
- Context indicator should show token/character counts

**Actual Behavior:**
- Context is sent to API but with literal strings "insights" or "full content" instead of actual data
- AI agent receives no actual content to work with
- Token/character counts are not displayed

## Problem Statement
The `buildContext` function in [useNotebookChat.ts](frontend/src/lib/hooks/useNotebookChat.ts:123-147) is building context objects with literal string values ("insights", "full content") instead of actually retrieving the content from the sources and notes. The API endpoint expects a format similar to what the Streamlit implementation uses, where the context contains actual content data that can be processed.

## Solution Statement
Modify the frontend to match the Streamlit implementation's two-step approach:
1. **Step 1**: Send context configuration (source/note IDs + their selection modes) to `/chat/context` endpoint
2. **Step 2**: Use the returned context object (containing actual fetched content + metadata) when calling `/chat/execute`
3. **Step 3**: Display token/character counts from the context response in a compact, informative UI

Currently, the React frontend skips both steps and sends literal placeholder strings directly to `/chat/execute`, which is why the AI has no actual content to work with.

## Steps to Reproduce
1. Open a notebook in the React frontend at `/notebooks/[id]`
2. Add at least one source or note to the notebook
3. Toggle the context selection for a source/note to "full" (blue icon)
4. Observe the context indicator shows "1 full" or similar but no token/char counts
5. Send a message in the chat asking about the content
6. Observe: AI responds without knowledge of the content

## Root Cause Analysis
The bug occurs in [useNotebookChat.ts:123-147](frontend/src/lib/hooks/useNotebookChat.ts:123-147) where the `buildContext` function creates a context object with literal strings:

```typescript
return {
  sources: sources
    .filter(source => {
      const mode = contextSelections.sources[source.id]
      return mode && mode !== 'off'
    })
    .map(source => {
      const mode = contextSelections.sources[source.id]
      return {
        id: source.id,
        content: mode === 'insights' ? 'insights' : 'full content'  // ❌ LITERAL STRINGS
      }
    }),
  notes: notes
    .filter(note => {
      const mode = contextSelections.notes[note.id]
      return mode && mode !== 'off'
    })
    .map(note => ({
      id: note.id,
      content: 'full content'  // ❌ LITERAL STRING
    }))
}
```

**Why this is wrong:**

1. **The `/chat/execute` endpoint needs actual content**: The API expects `request.context` to contain the actual fetched content from sources/notes, which gets injected into the LLM prompt template at [prompts/chat.jinja:17-22](prompts/chat.jinja:17-22)

2. **The correct flow** (from Streamlit [pages/stream_app/chat.py:22-61](pages/stream_app/chat.py:22-61)):
   - Build `context_config`: Map source/note IDs → status strings ("insights", "full content", "not in")
   - Call `/chat/context` with notebook_id + context_config → Get back actual content + token/char counts
   - Call `/chat/execute` with the actual content context

3. **The `/chat/context` endpoint** ([api/routers/chat.py:391-496](api/routers/chat.py:391-496)) does the heavy lifting:
   - Takes source/note IDs and their modes as input
   - Fetches actual Source and Note objects from database
   - Calls `source.get_context(context_size="short"/"long")` based on mode
   - Calls `note.get_context(context_size="long")`
   - Returns structured context with **actual text content + token_count + char_count**

**The React frontend is bypassing the `/chat/context` endpoint entirely and sending placeholder strings like "insights" and "full content" directly to `/chat/execute`, so the LLM receives literal strings instead of actual document content.**

## Relevant Files

### Files to Modify

- **[frontend/src/lib/hooks/useNotebookChat.ts:123-147](frontend/src/lib/hooks/useNotebookChat.ts:123-147)** - Contains the broken `buildContext` function that needs to be completely rewritten to use the API's `/chat/context` endpoint

- **[frontend/src/lib/api/chat.ts:62-68](frontend/src/lib/api/chat.ts:62-68)** - Already has `buildContext` API function, needs to be used by the hook

- **[frontend/src/lib/types/api.ts:208-223](frontend/src/lib/types/api.ts:208-223)** - Type definitions for `BuildContextRequest` and `BuildContextResponse` need to be verified/updated to match backend expectations

- **[frontend/src/components/common/ContextIndicator.tsx](frontend/src/components/common/ContextIndicator.tsx)** - Context indicator component needs to be enhanced to show token/char counts with a more compact layout

- **[frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx](frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx)** - Needs to pass token/char counts from the hook to the ContextIndicator component

### Files for Reference (No Changes)

- **[pages/stream_app/chat.py:22-47](pages/stream_app/chat.py:22-47)** - Working Streamlit implementation showing correct approach
- **[api/routers/chat.py:391-496](api/routers/chat.py:391-496)** - Backend `/chat/context` endpoint implementation
- **[api/chat_service.py:150-168](api/chat_service.py:150-168)** - Streamlit's service layer showing correct API usage

## Step by Step Tasks

### Step 1: Update Type Definitions
Verify and update the context-related type definitions to match the backend's expectations:

- Review [frontend/src/lib/types/api.ts:208-223](frontend/src/lib/types/api.ts:208-223)
- Ensure `BuildContextRequest.context_config` structure matches what the backend expects:
  ```typescript
  context_config: {
    sources: Record<string, string>  // id -> mode ("insights" | "full content" | "not in")
    notes: Record<string, string>    // id -> mode ("full content" | "not in")
  }
  ```
- Update `SendNotebookChatMessageRequest.context` to accept the full context response from `/chat/context`, not just the simple structure

### Step 2: Rewrite buildContext in useNotebookChat Hook
Replace the client-side context building with API-based context building:

- Modify [frontend/src/lib/hooks/useNotebookChat.ts:123-147](frontend/src/lib/hooks/useNotebookChat.ts:123-147)
- Create a new async `buildContext` function that:
  1. Constructs `context_config` from `contextSelections` state
  2. Calls `chatApi.buildContext()` with notebook_id and context_config
  3. Returns the full context response with actual content + token_count + char_count
- Update the function signature from synchronous to async
- Keep the filtering logic (mode !== 'off') but map to proper status strings
- Store token_count and char_count in component state

### Step 3: Update sendMessage to Use Async Context Building
Modify the sendMessage function to await context building:

- Update [frontend/src/lib/hooks/useNotebookChat.ts:150-214](frontend/src/lib/hooks/useNotebookChat.ts:150-214)
- Change `const context = buildContext()` to `const contextResponse = await buildContext()`
- Extract `context`, `token_count`, and `char_count` from the response
- Handle any errors from context building
- Ensure the context from the API is passed correctly to `chatApi.sendMessage()`

### Step 4: Update SendNotebookChatMessageRequest Type
Update the message request type to accept full context:

- Modify [frontend/src/lib/types/api.ts:198-206](frontend/src/lib/types/api.ts:198-206)
- Change the `context` field to match what `/chat/context` returns:
  ```typescript
  context: {
    sources: Array<Record<string, unknown>>
    notes: Array<Record<string, unknown>>
  }
  ```

### Step 5: Update ContextIndicator to Show Token/Char Counts
Enhance the context indicator UI to display token and character counts:

- Modify [frontend/src/components/common/ContextIndicator.tsx](frontend/src/components/common/ContextIndicator.tsx)
- Update the component props to accept `tokenCount` and `charCount`
- Redesign the layout to be more compact:
  - Show just numbers next to each icon (e.g., "📄 2" instead of "2 sources")
  - Move insights/full badges inline with numbers
  - Add token/char count display to the right side
  - Format as: "Context: 📄 2 (1 insights, 1 full) • 📝 1 • 1.2K tokens / 5K chars"
- Create a helper function to format large numbers (1234 → "1.2K", 1234567 → "1.2M")
- Ensure responsive layout that doesn't wrap awkwardly

### Step 6: Update useNotebookChat to Store and Return Token/Char Counts
Store the context metadata from the API response:

- Modify [frontend/src/lib/hooks/useNotebookChat.ts](frontend/src/lib/hooks/useNotebookChat.ts)
- Add state to store `tokenCount` and `charCount` from `/chat/context` response
- Update `buildContext` function to store these values when called
- Return them from the hook so `ChatColumn` can pass to `ContextIndicator`
- Update every time context selections change (via useEffect watching contextSelections)

### Step 7: Update ChatColumn to Pass Counts to ContextIndicator
Connect the token/char counts to the UI:

- Modify [frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx](frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx)
- Get `tokenCount` and `charCount` from the `useNotebookChat` hook
- Pass these values to `ChatPanel` via `notebookContextStats`
- Update the `NotebookContextStats` interface in [ChatPanel.tsx](frontend/src/components/source/ChatPanel.tsx) to include these fields

### Step 8: Verify API Integration
Ensure the frontend correctly communicates with both API endpoints:

- Verify [frontend/src/lib/api/chat.ts:62-68](frontend/src/lib/api/chat.ts:62-68) `buildContext` function
- Verify [frontend/src/lib/api/chat.ts:51-60](frontend/src/lib/api/chat.ts:51-60) `sendMessage` function
- Ensure both functions handle the updated types correctly

### Step 9: Test the Fix
Manually test the complete flow:

- Start the backend API server
- Start the frontend development server
- Create/open a notebook with sources and notes
- Toggle context selections (off/insights/full)
- Verify context indicator shows:
  - Correct counts with compact format (numbers next to icons)
  - Token and character counts on the right side
  - Updates in real-time as selections change
- Send chat messages and verify AI receives proper context
- Verify different context modes (insights vs full) work correctly

### Step 10: Run Validation Commands
Execute all validation commands to ensure no regressions:

- Run TypeScript type checking
- Run the build process
- Test the complete user flow

## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

- `cd frontend && npx tsc --noEmit` - Run TypeScript type checking to catch any type errors
- `cd frontend && npm run build` - Build the frontend to ensure no build errors
- Manual testing steps:
  1. Start backend: `make api` (or `uv run run_api.py`)
  2. Start frontend: `cd frontend && npm run dev`
  3. Open browser to `http://localhost:3000/notebooks/[test-notebook-id]`
  4. Add a test source and note
  5. Toggle source to "full" mode (blue icon)
  6. Verify context indicator shows:
     - Compact format: "📄 1 (1 full)" with token/char counts on right
     - Token count (e.g., "1.2K tokens")
     - Character count (e.g., "5K chars")
  7. Send message: "What does this source say?"
  8. Verify AI responds with content-aware answer (not "I don't have context")
  9. Toggle source to "insights" mode
  10. Verify context indicator updates to show "📄 1 (1 insights)"
  11. Send another message and verify AI uses insights-only context
  12. Toggle to "off" mode and verify AI says no context is available

## Notes

**Key Implementation Details:**

1. **Context Config Format**: The backend expects strings like "insights", "full content", "not in" as values in the context_config map. These are used as filters/indicators by the backend, not as actual content.

2. **API Flow**: The correct flow is:
   - Frontend builds `context_config` from user selections
   - Frontend calls `/chat/context` with config
   - Backend returns actual content + token_count + char_count based on config
   - Frontend uses returned context in `/chat/execute`
   - Frontend displays token/char counts in context indicator

3. **Streamlit Reference**: The working implementation is in [pages/stream_app/chat.py:22-47](pages/stream_app/chat.py:22-47) - use this as the gold standard for behavior.

4. **No New Dependencies**: This fix requires no new libraries or dependencies.

5. **Backward Compatibility**: The API endpoints haven't changed, so this fix maintains compatibility with the Streamlit frontend.

6. **Context Modes**:
   - Sources: "off" | "insights" | "full"
   - Notes: "off" | "full"
   - Backend API uses these exact strings in conditionals

7. **Error Handling**: Add proper error handling for the async buildContext call - if context building fails, show a user-friendly error and don't send the message.

8. **UI Enhancement - Context Indicator**:
   - The context indicator should show a more compact format to save space
   - Current format: "1 source", "1 full", "1 note" takes up too much space
   - New format: Show just numbers next to icons (📄 2, 💡 1, 📝 1)
   - Add token/char counts on the right: "1.2K tokens / 5K chars"
   - This gives a cleaner, more informative display
   - The `/chat/context` endpoint already returns `token_count` and `char_count` - just need to display them
   - Format large numbers with K/M suffixes (1234 → "1.2K", 1234567 → "1.2M")
