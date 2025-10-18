# AddSourceDialog Component

The `AddSourceDialog` component provides a comprehensive interface for adding new sources to notebooks with async processing support.

## Features

- **Multi-type source support**: Links, file uploads, and text content
- **Multi-notebook selection**: Add sources to multiple notebooks simultaneously  
- **Transformations**: Apply transformations during source processing
- **Async processing**: Background processing with status monitoring
- **Form validation**: Comprehensive validation with Zod and React Hook Form
- **File upload support**: Handle file uploads with progress indicators
- **Responsive design**: Works well on desktop and mobile

## Usage

### Basic Usage

```tsx
import { AddSourceDialog } from '@/components/sources'

function MyComponent() {
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <>
      <button onClick={() => setDialogOpen(true)}>
        Add Source
      </button>
      
      <AddSourceDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </>
  )
}
```

### With Default Notebook

```tsx
<AddSourceDialog
  open={dialogOpen}
  onOpenChange={setDialogOpen}
  defaultNotebookId="notebook:123"
/>
```

### Using the Button Component

```tsx
import { AddSourceButton } from '@/components/sources'

function MyComponent() {
  return (
    <AddSourceButton 
      defaultNotebookId="notebook:123"
      variant="outline"
      size="sm"
    />
  )
}
```

## Props

### AddSourceDialog

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `open` | `boolean` | - | Controls dialog visibility |
| `onOpenChange` | `(open: boolean) => void` | - | Called when dialog should open/close |
| `defaultNotebookId` | `string` | - | Pre-select a notebook |

### AddSourceButton

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `defaultNotebookId` | `string` | - | Pre-select a notebook in dialog |
| `variant` | `'default' \| 'outline' \| 'ghost'` | `'default'` | Button styling variant |
| `size` | `'sm' \| 'default' \| 'lg'` | `'default'` | Button size |
| `className` | `string` | - | Additional CSS classes |

## Source Types

### Link Sources
- Requires a valid URL
- Automatically extracts content from web pages
- Supports most web content formats

### File Upload Sources  
- Supports: PDF, DOC, DOCX, TXT, MD, EPUB
- Handles large files with async processing
- Shows upload progress

### Text Sources
- Direct text input
- Useful for pasting content
- Supports markdown formatting

## Processing Options

### Embedding
- **Enabled by default**: Makes sources searchable via vector search
- **Disable for**: Sources you don't want in search results

### Async Processing (Recommended)
- **Default**: Background processing for better UX
- **Benefits**: Non-blocking, handles large files, progress monitoring
- **Disable for**: Small sources that need immediate processing

## Integration with Hooks

The component integrates with several custom hooks:

- `useNotebooks()` - Fetches available notebooks
- `useTransformations()` - Fetches available transformations  
- `useCreateSource()` - Handles source creation
- `useSourceStatus()` - Monitors processing status

## Error Handling

The component includes comprehensive error handling:

- Form validation errors are shown inline
- Network errors show toast notifications
- File upload errors are handled gracefully
- Processing errors are displayed with retry options

## Accessibility

- Full keyboard navigation support
- Screen reader friendly
- ARIA labels and descriptions
- Focus management

## Dependencies

- React Hook Form for form handling
- Zod for validation
- TanStack Query for data fetching
- shadcn/ui for components
- Lucide React for icons