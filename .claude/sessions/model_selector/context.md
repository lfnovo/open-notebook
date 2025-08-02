# Model Management Feature - Context

## Purpose
Replicate the model management functionality from the existing Streamlit UI (`pages/7_🤖_Models.py`) into the new React frontend, with improvements to the API layer.

## Current State
- **Streamlit UI**: Has a working model management page that checks provider availability via environment variables
- **API Layer**: Has CRUD endpoints for models and default model management
- **Missing**: API endpoint for provider availability checks (currently done in Streamlit)

## What Needs to Be Built

### API Enhancement
1. **New Endpoint**: `GET /api/models/providers`
   - Returns available/unavailable providers based on environment variables
   - Includes which model types each provider supports (using Esperanto's `AIFactory.get_available_providers()`)
   - Format: `{ available: [...], unavailable: [...], supported_types: {...} }`

### React Frontend Page
1. **Model Management Page** at `/models` route
   - Display provider availability status (available vs unavailable)
   - Show configured models grouped by type (language, embedding, TTS, STT)
   - Allow adding new models (only from available providers)
   - Allow deleting existing models
   - Set default models for each purpose
   - Use shadcn/ui components for better UX

## Key Requirements
1. **Provider Validation**: Only allow adding models from providers that have API keys configured
2. **Type Support**: Use Esperanto to determine which providers support which model types
3. **UI/UX**: Follow the same functionality as Streamlit but with improved design using shadcn/ui
4. **Error Handling**: Proper loading states, error messages, and user feedback

## User Flow
1. User navigates to Models page
2. Sees provider availability status at the top
3. Views configured models grouped by type
4. Can add new models via forms (provider dropdown filtered by availability)
5. Can delete models with confirmation
6. Can set default models via dropdowns
7. Changes are immediately reflected and persisted

## Technical Constraints
- Must integrate with existing API client and React Query setup
- Should follow patterns established in Phase 2
- Use existing shadcn/ui components
- Maintain TypeScript type safety throughout