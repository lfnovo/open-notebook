# Chore: Remove Insights Count from Details Tab

## Chore Description
In the source detail page under the frontend app, there are 3 tabs for source information: Content, Insights, and Details. The Details tab currently displays an "Insights" count in its Statistics section, which is redundant since the Insights tab already shows the count in its tab trigger (e.g., "Insights (1)"). This chore removes the redundant insights count display from the Details tab to avoid duplication and improve UI clarity.

## Relevant Files
Use these files to resolve the chore:

- **`frontend/src/components/source/SourceDetailContent.tsx`** (lines 710-716)
  - This is the main component that renders the source detail page with tabs
  - Contains the Details tab with the Statistics section showing the redundant insights count
  - Need to remove the insights count row from the Statistics section while keeping the "Embedded" status

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Remove Insights Count from Statistics Section
- Open `frontend/src/components/source/SourceDetailContent.tsx`
- Locate the Statistics section in the Details tab (lines 697-718)
- Remove the insights count display (lines 710-716) which shows:
  ```tsx
  <div className="flex items-center justify-between">
    <div className="flex items-center gap-2">
      <FileText className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm">Insights</span>
    </div>
    <span className="font-semibold">{source.insights_count || 0}</span>
  </div>
  ```
- Keep the "Embedded" status display (lines 700-709) intact
- Ensure proper formatting and spacing after removal

### Step 2: Verify the Change
- Run the development server with `cd frontend && npm run dev`
- Navigate to a source detail page
- Verify that:
  - The Details tab no longer shows the "Insights" count in the Statistics section
  - The "Embedded" status is still displayed correctly
  - The Insights tab still shows the count in its tab trigger (e.g., "Insights (1)")
  - All three tabs (Content, Insights, Details) render properly

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `cd frontend && npm run build` - Ensure the frontend builds successfully without TypeScript or build errors

## Notes
- The `FileText` icon import on line 34 can remain as it may be used elsewhere in the component
- The `source.insights_count` property is still used in the Insights tab trigger (line 410), so we're only removing the duplicate display from the Details tab
- This change improves UI consistency by having the insights count displayed only once (in the Insights tab trigger)
