# Bulk Source Action Feature

## Overview
This feature adds bulk action capabilities for including/excluding sources in a chat session for notebooks. When dealing with a high number of sources, this feature saves time by avoiding unnecessary scrolls multiple times per session.

## Implementation Details

### Backend Changes

1. **API Endpoint**: Added a new endpoint `/api/notebooks/{notebook_id}/sources/bulk` that supports bulk operations (add/remove) for sources in a notebook.

2. **Request Model**: 
   - `BulkSourceOperationRequest` with fields:
     - `source_ids`: List of source IDs to operate on
     - `operation`: Either "add" or "remove"

3. **Response Model**:
   - `BulkSourceOperationResponse` with:
     - `message`: Summary of the operation
     - `results`: Detailed results for each source operation

### Frontend Changes

1. **API Client**: Updated the notebooks API client to include the new `bulkSourceOperation` method.

2. **Hooks**: Added `useBulkSourceOperation` hook in `use-sources.ts` to handle bulk operations with proper error handling and UI feedback.

3. **UI Components**: 
   - Created `BulkSourceActionDialog` component for selecting multiple sources
   - Updated `SourcesColumn` component to include bulk action options in the dropdown menu

4. **User Experience**:
   - Added "Bulk Add Sources" and "Bulk Remove Sources" options to the sources dropdown
   - Implemented select-all functionality in the bulk action dialog
   - Added visual feedback for selected sources count
   - Integrated with existing toast notifications for operation results

## How to Use

1. Navigate to a notebook page
2. Click the "Add Source" dropdown button in the Sources column
3. Select either "Bulk Add Sources" or "Bulk Remove Sources"
4. In the dialog that appears:
   - Use the checkboxes to select which sources to include/exclude
   - Use the "Select All" checkbox to quickly select/deselect all sources
   - Click the action button to perform the bulk operation
5. The sources will be added/removed from the notebook in a single operation

## Benefits

- **Time Savings**: Eliminates the need to individually add/remove many sources
- **Efficiency**: Reduces repetitive scrolling and clicking when managing large numbers of sources
- **User Experience**: Provides a more streamlined workflow for source management
- **Error Handling**: Gracefully handles partial failures with detailed feedback

## Technical Notes

- The implementation follows the existing code patterns and conventions
- All operations are atomic - if one source fails, others continue to process
- Proper error handling and user feedback is implemented
- The feature integrates seamlessly with existing source management workflows