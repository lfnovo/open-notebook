# Feature: Chat Message Actions (Save to Note & Copy)

## Feature Description
Add action buttons to AI messages in the notebook chat interface that allow users to:
1. Save an AI response as a new note in the current notebook
2. Copy the AI message content to clipboard

This feature replicates the functionality from the Streamlit app where users could click a "💾 New Note" button on AI messages. The new React implementation will provide a more modern, accessible interface with two key actions: saving messages as notes and copying message content.

## User Story
As a notebook user
I want to save valuable AI responses as notes and copy message content
So that I can preserve important insights in my notebook for future reference and share content with others

## Problem Statement
Currently in the React frontend, users can only read AI responses in the chat interface but cannot easily preserve them as permanent notes or share them. In the previous Streamlit version, users could click a button to save AI messages as notes, which was a valuable workflow for capturing insights. Users also need the ability to quickly copy message content for use in other applications.

## Solution Statement
Add two action buttons to AI messages in the ChatPanel component:
1. A "Save to Note" button that creates a new AI-type note with the message content
2. A "Copy" button that copies the message content to the clipboard

These buttons will appear on hover/focus for AI messages, maintaining a clean interface while providing easy access to these actions. When a note is created, the notes list will automatically refresh to show the new note immediately.

## Relevant Files
Use these files to implement the feature:

- **[frontend/src/components/source/ChatPanel.tsx](frontend/src/components/source/ChatPanel.tsx)** - Main chat panel component that renders messages. This is where we'll add the action buttons to AI messages.

- **[frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx](frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx)** - Notebook chat column wrapper that manages the notebook chat state. We'll need to pass the notebookId down for note creation.

- **[frontend/src/lib/hooks/useNotebookChat.ts](frontend/src/lib/hooks/useNotebookChat.ts)** - Hook that manages notebook chat state. We may need to add logic here to trigger note refreshes.

- **[frontend/src/lib/hooks/use-notes.ts](frontend/src/lib/hooks/use-notes.ts)** - Hook providing the `useCreateNote` mutation for creating notes. We'll use this existing functionality.

- **[frontend/src/lib/api/notes.ts](frontend/src/lib/api/notes.ts)** - Notes API client with `create` method that calls `POST /notes`.

- **[frontend/src/lib/types/api.ts](frontend/src/lib/types/api.ts)** - TypeScript type definitions including `CreateNoteRequest` and `NoteResponse`.

- **[frontend/src/app/(dashboard)/notebooks/components/NotesColumn.tsx](frontend/src/app/(dashboard)/notebooks/components/NotesColumn.tsx)** - Notes column component that displays the list of notes. This will automatically refresh when new notes are created due to React Query cache invalidation.

### New Files
No new files need to be created. We'll enhance existing components with new functionality.

## Implementation Plan

### Phase 1: Foundation
1. Review the existing ChatPanel component structure to understand message rendering
2. Identify where AI message actions should be added in the component hierarchy
3. Confirm the note creation API flow and data requirements
4. Review clipboard API browser compatibility

### Phase 2: Core Implementation
1. Create a new MessageActions component to render the action buttons
2. Implement "Save to Note" functionality using the existing `useCreateNote` hook
3. Implement "Copy to Clipboard" functionality using the Clipboard API
4. Add proper error handling and user feedback (toasts)
5. Style the action buttons to appear on hover/focus for a clean UX

### Phase 3: Integration
1. Integrate MessageActions into ChatPanel's AI message rendering
2. Pass necessary props (notebookId) through the component hierarchy
3. Ensure notes list refreshes automatically after note creation via React Query cache invalidation
4. Test the complete workflow end-to-end
5. Handle edge cases (clipboard permissions, note creation failures, etc.)

## Step by Step Tasks

### Step 1: Create MessageActions Component
- Create a new component file at `frontend/src/components/source/MessageActions.tsx`
- Implement two buttons: "Save to Note" and "Copy"
- Use lucide-react icons: `Save` for save to note, `Copy` for copy
- Add hover/focus states for better UX
- Make the component appear on message hover using CSS

### Step 2: Add Note Creation Functionality
- Import and use `useCreateNote` hook from `use-notes.ts`
- Implement `handleSaveToNote` function that:
  - Calls the create note mutation with the message content
  - Sets `note_type: "ai"`
  - Includes the `notebook_id` from props
  - Shows success toast on completion
  - Shows error toast on failure

### Step 3: Add Copy to Clipboard Functionality
- Implement `handleCopyToClipboard` function using `navigator.clipboard.writeText()`
- Add fallback for older browsers using `document.execCommand('copy')`
- Show success toast: "Message copied to clipboard"
- Show error toast if clipboard access fails
- Handle clipboard permissions gracefully

### Step 4: Update ChatPanel to Support Actions
- Modify the ChatPanel component to accept an optional `notebookId` prop
- Pass `notebookId` to the AI message rendering section
- Integrate MessageActions component into the AI message container
- Position the action buttons appropriately (top-right corner of message bubble)
- Ensure actions only appear for AI messages, not human messages

### Step 5: Update ChatColumn to Pass NotebookId
- Modify `ChatColumn.tsx` to pass `notebookId` prop to `ChatPanel`
- Verify the prop is correctly threaded through the component hierarchy

### Step 6: Handle Thinking Content
- Review how thinking content is parsed and displayed (based on Streamlit implementation)
- Ensure the "Save to Note" action saves the full message content including thinking blocks
- Ensure the "Copy" action copies the full content including thinking blocks

### Step 7: Add Loading States
- Add loading state to "Save to Note" button while note creation is in progress
- Disable both buttons during note creation to prevent duplicate submissions
- Show spinner icon during loading

### Step 8: Test Edge Cases
- Test with messages containing markdown formatting
- Test with messages containing source references
- Test with very long messages
- Test with messages containing thinking content
- Test clipboard functionality in different browsers
- Test note creation failure scenarios
- Test when notebook_id is not provided (graceful degradation)

### Step 9: Verify Cache Invalidation
- Confirm that creating a note automatically refreshes the notes list
- Verify that the new note appears immediately in the NotesColumn
- Test that React Query's cache invalidation is working correctly
- Ensure no manual page refresh is needed

### Step 10: Run Validation Commands
- Execute all validation commands listed in the "Validation Commands" section
- Fix any issues or regressions discovered
- Verify zero test failures
- Ensure the feature works correctly in development and production builds

## Testing Strategy

### Unit Tests
- Test MessageActions component in isolation
  - Test save to note button triggers correct API call
  - Test copy button calls clipboard API
  - Test loading states during async operations
  - Test error handling for failed operations
  - Test that buttons are only rendered for AI messages

### Integration Tests
- Test the complete flow from chat message to saved note
  - Send a message in notebook chat
  - Click "Save to Note" on AI response
  - Verify note appears in notes list
  - Verify note has correct content and type ("ai")
- Test clipboard functionality
  - Click "Copy" button
  - Verify content is in clipboard
  - Verify success toast appears

### Edge Cases
- Message with markdown formatting (verify formatting is preserved in note)
- Message with source references (verify references are preserved)
- Very long messages (verify full content is saved/copied)
- Messages with thinking content (verify thinking blocks are included)
- Clipboard permission denied (verify graceful error handling)
- Note creation API failure (verify error toast and no crash)
- Missing notebookId prop (verify graceful degradation)
- Multiple rapid clicks on save button (verify only one note is created)
- Network timeout during note creation (verify appropriate error message)

## Acceptance Criteria
1. ✅ AI messages in notebook chat display two action buttons on hover: "Save to Note" and "Copy"
2. ✅ Clicking "Save to Note" creates a new AI-type note with the message content
3. ✅ The newly created note appears immediately in the NotesColumn without requiring a page refresh
4. ✅ Clicking "Copy" copies the message content to the clipboard
5. ✅ Success toasts appear when actions complete successfully
6. ✅ Error toasts appear when actions fail with helpful error messages
7. ✅ Buttons show loading states during async operations
8. ✅ Full message content (including thinking blocks) is saved/copied
9. ✅ Markdown formatting and source references are preserved
10. ✅ Action buttons only appear on AI messages, not human messages
11. ✅ The feature works in all major browsers (Chrome, Firefox, Safari, Edge)
12. ✅ No regressions in existing chat functionality

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

### Frontend Commands
- `cd frontend && npm run build` - Verify frontend builds without errors
- `cd frontend && npm run typecheck` - Ensure no TypeScript errors (if type checking is configured)
- `cd frontend && npm run lint` - Verify code follows linting standards (if linting is configured)

### Backend Commands (ensure no regressions)
- `cd /Users/luisnovo/dev/projetos/open-notebook/open-notebook && uv run python -m pytest tests/ -v` - Run all backend tests to ensure no API regressions

### Manual Testing Steps
1. Start the development environment:
   - `make database` - Start SurrealDB
   - `make api` - Start FastAPI backend
   - `cd frontend && npm run dev` - Start Next.js frontend
2. Navigate to a notebook page
3. Send a message in the chat
4. Hover over the AI response message
5. Verify both "Save to Note" and "Copy" buttons appear
6. Click "Save to Note" and verify:
   - Loading state appears briefly
   - Success toast shows "Note created successfully"
   - New note appears in the Notes column
   - Note contains the AI message content
   - Note is marked as "AI Generated"
7. Click "Copy" and verify:
   - Success toast shows "Message copied to clipboard"
   - Paste in another application to confirm content was copied
8. Test with various message types (markdown, with references, long messages)
9. Test error scenarios (disconnect network and try to save)
10. Verify existing chat functionality still works (sending messages, sessions, etc.)

## Clarification Needed
None at this time. The requirements are clear based on the existing Streamlit implementation and the codebase structure.

## Notes

### Implementation Details
- The note creation API (`POST /notes`) already handles auto-generating titles for AI notes, so we don't need to provide a title when creating notes from chat messages
- React Query automatically invalidates the notes cache when a new note is created (via `useCreateNote` hook), so the NotesColumn will refresh automatically
- The existing `useCreateNote` hook already shows success/error toasts, so we get that functionality for free

### Browser Compatibility
- The Clipboard API (`navigator.clipboard.writeText()`) is supported in all modern browsers
- We should include a fallback using `document.execCommand('copy')` for older browsers
- Consider checking for clipboard permissions before attempting to copy

### Future Enhancements
- Add keyboard shortcuts (e.g., Cmd/Ctrl + S to save message to note)
- Add option to edit the note title before saving
- Add option to select which notebook to save to (for multi-notebook scenarios)
- Add "Share" button to share message via native share API
- Add "Regenerate" button to re-run the query with the same context

### Design Considerations
- Action buttons should be subtle and only appear on hover to maintain clean UI
- Use consistent iconography with the rest of the application
- Ensure buttons are accessible (keyboard navigation, screen readers)
- Consider mobile UX where hover states don't exist (show buttons always on mobile)

### Performance Considerations
- Note creation should be fast (< 1 second in most cases due to title generation)
- Show loading states immediately on button click for user feedback
- Clipboard operations are synchronous and very fast (< 100ms)
- React Query's cache invalidation is efficient and won't cause unnecessary re-renders
