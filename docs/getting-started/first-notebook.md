# Your First Notebook - A Complete Walkthrough

Welcome to Open Notebook! This guide will walk you through creating your first notebook and experiencing all the core features that make Open Notebook a powerful research and note-taking tool. By the end of this walkthrough, you'll have created a notebook, added sources, generated AI insights, and learned how to effectively use the chat assistant.

## Understanding the Interface

Open Notebook uses a clean three-column layout designed to optimize your research workflow:

- **Left Column**: Your sources and notes - all the content you've added to your notebook
- **Middle Column**: The main workspace where you'll interact with transformations and view detailed content
- **Right Column**: The AI chat assistant and context management

This layout keeps your sources visible while you work, making it easy to reference materials and manage what information the AI can access.

## Step 1: Creating Your First Notebook

Let's start by creating a notebook for a sample research project.

1. **Click "New Notebook"** on the main dashboard
2. **Choose a descriptive name** - for this example, let's use "Climate Change Research"
3. **Write a detailed description** - this is crucial as it helps the AI understand your research context

   Example description:
   ```
   Research notebook focused on climate change impacts, solutions, and policy. 
   Collecting information from scientific papers, news articles, and expert interviews 
   to understand current trends and potential mitigation strategies.
   ```

![New Notebook](/assets/new_notebook.png)

4. **Click "Create Notebook"**

**💡 Pro Tip**: The more detailed your description, the better the AI will understand your research goals and provide relevant insights.

## Step 2: Adding Your First Sources

Now let's add different types of content to your notebook. We'll add three different source types to demonstrate the flexibility.

### Adding a Web Article

1. **Click "Add Source"** in the left column
2. **Select "Link"** as your source type
3. **Paste a URL** - try this example: `https://www.ipcc.ch/report/ar6/wg1/`
4. **Add a title** like "IPCC Climate Report"
5. **Click "Add Source"**

The system will automatically scrape the content and make it searchable.

![Add Source](/assets/add_source.png)

### Adding a Text Note

1. **Click "Add Source"** again
2. **Select "Text"** as your source type
3. **Paste or type content** - you can add research notes, quotes, or any text content
4. **Give it a descriptive title** like "Key Climate Statistics"
5. **Click "Add Source"**

### Adding a File

1. **Click "Add Source"** one more time
2. **Select "File"** as your source type
3. **Upload a PDF, document, or other supported file**
4. **The system will automatically extract the text content**

You'll now see all your sources listed in the left column:

![Asset List](/assets/asset_list.png)

## Step 3: Generating Your First AI Insights

Now that you have content, let's generate some AI insights using transformations.

1. **Click on one of your sources** in the left column
2. **Look for the "Transformations" section** in the middle column
3. **Try a pre-built transformation** like "Summarize" or "Key Points"
4. **Click "Generate"** to create your first AI insight

![Transformations](/assets/transformations.png)

The AI will analyze your content and provide insights based on the transformation you selected. These insights can be saved as notes for future reference.

**💡 Pro Tip**: Transformations are customizable prompts. You can create your own transformations for specific research needs, like "Extract methodology" or "Identify key arguments."

## Step 4: Understanding Context Settings

Before chatting with the AI, it's important to understand how context works. This is one of Open Notebook's most powerful features.

![Context Settings](/assets/context.png)

For each source, you can set:

- **Not in Context**: The AI won't see this content (saves on API costs)
- **Summary**: The AI gets a summary and can request full content if needed (balanced approach)
- **Full Content**: The AI gets the complete text (most comprehensive but uses more tokens)

### Setting Up Context for Your First Chat

1. **Click on the context toggle** next to each source
2. **For your first try, set one source to "Full Content"**
3. **Set others to "Summary"** to balance cost and performance
4. **Leave any sensitive sources as "Not in Context"**

## Step 5: Your First Chat with the AI

Now let's have a conversation with the AI assistant about your research.

1. **Look at the right column** for the chat interface
2. **Type your first question** - try something like:
   ```
   What are the main causes of climate change discussed in my sources?
   ```
3. **Press Enter** to send your question

The AI will analyze your sources (based on your context settings) and provide a comprehensive answer. Notice how it references specific sources in its response.

### Try These Follow-up Questions:

- "What solutions are mentioned for addressing climate change?"
- "Can you compare the different perspectives in my sources?"
- "What are the key statistics I should remember?"

## Step 6: Saving Important Information as Notes

When the AI provides a particularly useful response, you can save it as a note:

1. **Look for the "Save as Note" button** under any AI response
2. **Click it** to convert the response into a permanent note
3. **Edit the title** if needed
4. **The note will appear in your left column** for easy reference

![AI Notes](/assets/ai_note.png)

You can also create manual notes:

1. **Click "Add Note"** in the left column
2. **Write your own observations** or insights
3. **Save** to keep them with your research

![Human Notes](/assets/human_note.png)

## Step 7: Working with Multiple Chat Threads

For complex research, you might want separate conversations:

1. **Look for the "New Chat" option** in the chat interface
2. **Create topic-specific chats** like:
   - "Policy Analysis"
   - "Technical Details"
   - "Literature Review"

Each chat maintains its own context and history, helping you stay organized.

## Step 8: Using Search Across Your Research

As your notebook grows, use the search feature to find information quickly:

1. **Go to the Search page** (if available in your interface)
2. **Search by keywords** or use semantic search
3. **Find relevant notes and sources** across all your notebooks

![Search](/assets/search.png)

## Next Steps for Deeper Exploration

Congratulations! You've successfully created your first notebook and experienced the core features. Here are some next steps to explore:

### Advanced Features to Try:

1. **Custom Transformations**: Create your own analysis prompts for specific research needs
2. **Podcast Generation**: Convert your research into audio summaries
3. **Advanced Context Management**: Experiment with different context settings for optimal AI interactions
4. **Source Organization**: Develop a system for categorizing and managing your sources

### Best Practices to Develop:

1. **Regular Note-Taking**: Save important AI insights as notes for future reference
2. **Context Optimization**: Use the minimum context needed for each conversation to save costs
3. **Descriptive Naming**: Give your notebooks and sources clear, searchable names
4. **Source Diversity**: Mix different types of content (articles, documents, personal notes) for richer insights

### Getting Help:

- **Documentation**: Explore the full documentation for advanced features
- **Community**: Join GitHub discussions for tips and feature requests
- **Support**: Check the troubleshooting section for common issues

## Troubleshooting Common First-Time Issues

**Sources not processing**: Wait a few moments for content extraction, especially for large files.

**AI not responding**: Check that you have at least one source set to "Summary" or "Full Content" in your context settings.

**Poor AI responses**: Try providing more context or asking more specific questions.

**Missing features**: Ensure your deployment includes all necessary AI model configurations.

## Summary

You've now experienced the complete Open Notebook workflow:

✅ Created a notebook with a detailed description  
✅ Added multiple types of sources (web, text, file)  
✅ Generated AI insights using transformations  
✅ Configured context settings for privacy and cost control  
✅ Chatted with the AI assistant about your research  
✅ Saved important insights as notes  
✅ Learned about advanced features and best practices  

Open Notebook is designed to grow with your research needs. As you add more sources and develop your workflow, you'll discover even more powerful ways to organize, analyze, and understand your research materials.

Happy researching! 🎉