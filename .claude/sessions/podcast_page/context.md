# Podcast Page UX Redesign - Context Document

## 🎯 **Why This is Being Built**

The current Podcast page has a confusing 3-tab interface (Episodes, Speaker Profiles, Episode Profiles) that makes users unclear about the relationship between speaker profiles and episode profiles. Users don't understand they need to create speaker profiles before episode profiles, leading to workflow confusion.

## 🎁 **Expected Outcome**

A streamlined 2-tab Podcast page:
1. **Episodes Tab**: Lists generated episodes (unchanged)
2. **Episode Templates Tab**: Combined episode profiles + speaker profiles management in a single interface that guides users naturally through the creation workflow.

## 🏗️ **How It Should Be Built**

### **Page Layout**
- **Header Section**: Explanatory paragraph about how episode profiles depend on speaker profiles and the creation workflow
- **Tab 1: Episodes**: List generated podcast episodes (keep current functionality)
- **Tab 2: Episode Templates**: Combined episode profiles + speaker profiles management
  - **Main Area**: Episode profiles management (primary focus)
  - **Side Column**: Speaker profiles overview/management (secondary)
  - **Dialogs**: Speaker profile creation/editing using `st.dialog`

### **Dialog Strategy** 
- **"Configure Speaker" button** in episode profile → Dialog with dropdown of existing speakers + "Create New" option
- **"Create New Speaker"** → Full speaker creation form within dialog
- **"Edit Speaker"** → Pre-populated form (same as create, just with existing data)

### **Speaker Profiles Column**
- Show all speaker profiles with usage indicators (highlight which ones are referenced by episode profiles)
- Provide duplicate, edit, delete actions via buttons
- Edit/create actions open dialogs (no inline forms)

### **Speaker Profile Information Display**
- Show speaker details directly within episode profile containers
- No separate "view-only" dialog needed - display info inline

## 🔧 **Testing Approach**

- Test creation workflow: create speaker profile → create episode profile that references it
- Test inline workflow: create episode profile → create speaker profile via dialog when needed
- Test editing flows for both profile types
- Verify speaker profile usage indicators work correctly
- Test all dialog interactions and form validations

## 📚 **Dependencies**

- Current API endpoints for speaker profiles and episode profiles (already implemented)
- Streamlit `st.dialog` functionality
- Existing validation logic in domain models
- Current Streamlit form components and session state management

## 🚧 **Constraints**

- Must maintain existing data models and API contracts
- Must preserve all current functionality (CRUD operations)
- Use existing validation rules from domain models
- Keep current API service pattern for data operations

## 🎨 **UI/UX Principles**

- **Primary focus**: Episode profiles (main content area)
- **Secondary support**: Speaker profiles (side column)
- **Progressive disclosure**: Use dialogs for complex forms
- **Context awareness**: Show relevant information at the right time
- **Clear hierarchy**: Guide users through the natural workflow

## 📝 **Header Explanation Content**

The header should explain:
- Episode profiles define the format and AI models for podcast generation
- Speaker profiles define the voices and personalities that will be used
- Episode profiles reference speaker profiles by name
- Recommended workflow: Create speaker profiles first, then episode profiles that use them
- Alternative: Create episode profiles and add speaker profiles on-demand via dialogs