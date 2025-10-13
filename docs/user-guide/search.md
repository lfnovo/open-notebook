# Search User Guide

Open Notebook provides powerful search capabilities to help you find information quickly across your entire knowledge base. This guide covers both traditional search methods and AI-powered question answering.

## Overview

Open Notebook offers two main search approaches:

1. **Direct Search** - Find specific content using text or vector search
2. **Ask Your Knowledge Base** - Get AI-generated answers based on your content

## Direct Search

### Search Types

#### Text Search
Text search uses full-text indexing with BM25 ranking to find exact matches and similar terms across your content.

**Best for:**
- Finding specific keywords, phrases, or terms
- Locating exact quotes or references
- Technical terms and proper nouns
- When you know approximately what you're looking for

**Search Coverage:**
- **Sources**: Title, full text content, embedded chunks, and insights
- **Notes**: Title and content

**Features:**
- Highlighted search results show matching terms
- BM25 relevance scoring
- Stemming and lowercase matching
- Punctuation and camel case tokenization

#### Vector Search
Vector search uses semantic embeddings to find conceptually similar content, even when exact keywords don't match.

**Best for:**
- Finding concepts and ideas
- Discovering related content
- Exploring themes and topics
- When you're not sure of exact terminology

**Requirements:**
- An embedding model must be configured (see [Models Guide](../models.md))
- Content must be processed with embeddings

**Search Coverage:**
- **Sources**: Embedded content chunks and insights
- **Notes**: Full note content (with embeddings)

**Features:**
- Cosine similarity scoring
- Configurable minimum similarity threshold (default: 0.2)
- Semantic understanding of content relationships

### Search Interface

#### Basic Search
1. Go to the **Search** tab in the "Ask and Search" page
2. Enter your search query
3. Select search type (Text or Vector)
4. Choose what to search:
   - **Search Sources**: Include imported documents and content
   - **Search Notes**: Include your personal notes
5. Click **Search**

#### Search Results
Results are displayed with:
- **Relevance/Similarity Score**: Higher scores indicate better matches
- **Title**: Content title or note title
- **Content Preview**: Matching text excerpt
- **Source Link**: Click to view the full source or note
- **Highlights**: Matching terms highlighted in text search

### Search Tips

#### Text Search Best Practices
- Use specific keywords for better results
- Try different variations of terms
- Use quotes for exact phrase matching
- Include technical terms and acronyms
- Be specific rather than general

**Examples:**
```
machine learning algorithms
"neural network architecture"
API documentation
React hooks
```

#### Vector Search Best Practices
- Use natural language descriptions
- Focus on concepts rather than exact words
- Describe what you're looking for thematically
- Use complete sentences or phrases

**Examples:**
```
How to optimize database performance
Strategies for team collaboration
Best practices for code review
User interface design principles
```

### Search Filters and Options

#### Content Type Filters
- **Search Sources**: Include imported documents, PDFs, web pages, etc.
- **Search Notes**: Include your personal notes and AI-generated content

#### Search Parameters
- **Limit**: Maximum number of results (default: 100, max: 1000)
- **Minimum Score**: For vector search, set similarity threshold (0.0 to 1.0)

### Advanced Search Techniques

#### Combining Search Types
1. Start with vector search for broad concept discovery
2. Use text search for specific details
3. Cross-reference results between search types

#### Iterative Search Strategy
1. Begin with broader terms
2. Refine based on initial results
3. Use discovered keywords for follow-up searches
4. Explore related concepts found in results

#### Search Result Analysis
- Pay attention to similarity/relevance scores
- Look for patterns in top results
- Use result previews to assess relevance
- Follow source links for full context

## Ask Your Knowledge Base

The Ask feature uses AI to generate comprehensive answers based on your content, combining multiple search queries automatically.

### How It Works

1. **Query Strategy**: AI analyzes your question and generates multiple search queries
2. **Individual Searches**: Each query is processed using vector search
3. **Individual Answers**: AI generates answers for each search result
4. **Final Answer**: All individual answers are combined into a comprehensive response

### Requirements

- **Embedding Model**: Required for vector search functionality
- **Three AI Models**:
  - **Query Strategy Model**: Powerful model for search planning (GPT-4, Claude, etc.)
  - **Individual Answer Model**: Can be faster/cheaper model (GPT-4 Mini, etc.)
  - **Final Answer Model**: Powerful model for synthesis (GPT-4, Claude, etc.)

### Using the Ask Feature

1. Go to the **Ask Your Knowledge Base** tab
2. Enter your question in natural language
3. Select your AI models for each processing stage
4. Click **Ask**

### Model Selection Guidelines

#### Query Strategy Model
**Recommended**: GPT-4, Claude Sonnet, Gemini Pro, Llama 3.2
- Needs strong reasoning for search strategy
- Determines what information to look for
- Critical for answer quality

#### Individual Answer Model
**Recommended**: GPT-4 Mini, Gemini Flash, cheaper models
- Processes individual search results
- Can use faster models for efficiency
- Multiple instances run in parallel

#### Final Answer Model
**Recommended**: GPT-4, Claude Sonnet, Gemini Pro
- Synthesizes all information
- Creates coherent final response
- Benefits from strong language capabilities

### Question Types

#### Factual Questions
```
What are the main benefits of microservices architecture?
How does React handle state management?
What security measures are recommended for APIs?
```

#### Analytical Questions
```
Compare different database indexing strategies
Analyze the pros and cons of remote work policies
What are the trade-offs between SQL and NoSQL databases?
```

#### Synthesis Questions
```
Summarize the key findings from my research on user experience
What patterns emerge from my project retrospectives?
How do different sources approach machine learning optimization?
```

### Answer Features

#### Citations and References
- Answers include links to source documents
- Click citations to view original content
- Source attribution for fact-checking
- Transparency in information sources

#### Saving Answers
- Save AI-generated answers as notes
- Select target notebook
- Preserved as "AI" note type
- Maintains question-answer format

### Best Practices

#### Effective Questions
- Be specific about what you need
- Provide context when helpful
- Ask follow-up questions to drill down
- Use natural language

#### Question Examples
**Good:**
```
How do the papers in my collection approach neural network optimization?
What are the common themes in my customer feedback notes?
Based on my research, what are the best practices for API design?
```

**Less Effective:**
```
Tell me about AI
What's in my notes?
Help me understand stuff
```

#### Managing Model Costs
- Use cheaper models for individual answers
- Reserve powerful models for strategy and final synthesis
- Monitor token usage in model settings
- Consider using local models for frequent queries

## Search Performance Optimization

### Content Preparation
- **Source Processing**: Ensure sources are properly imported and processed
- **Note Organization**: Well-structured notes improve search results
- **Embedding Coverage**: Verify content has embeddings for vector search

### Search Strategy
- **Progressive Refinement**: Start broad, then narrow down
- **Mixed Approach**: Combine text and vector search
- **Result Evaluation**: Review search scores and relevance

### System Optimization
- **Embedding Model**: Choose appropriate model for your use case
- **Index Health**: Ensure search indices are properly maintained
- **Content Volume**: Balance between comprehensive coverage and search speed

## Integration with Notes and Chat

### Saving Search Results
- **Direct Saving**: Save useful search results as notes
- **Answer Preservation**: Save AI-generated answers for reference
- **Notebook Organization**: Organize saved searches by topic

### Search in Workflow
1. **Research Phase**: Use search to gather relevant information
2. **Analysis Phase**: Ask targeted questions about findings
3. **Synthesis Phase**: Combine insights into new notes
4. **Review Phase**: Search for related content and updates

### Chat Integration
- Use search results to inform chat conversations
- Ask follow-up questions based on search findings
- Reference search results in chat for context

## Troubleshooting

### Common Issues

#### No Vector Search Available
**Problem**: Vector search option not showing
**Solution**: Configure an embedding model in the Models section

#### Poor Search Results
**Problem**: Search returns irrelevant results
**Solutions**:
- Try different keywords or phrases
- Switch between text and vector search
- Check search filters (sources/notes)
- Verify content has been properly processed

#### Ask Feature Not Working
**Problem**: Ask feature shows errors
**Solutions**:
- Ensure embedding model is configured
- Verify all three AI models are selected
- Check model API keys and settings
- Confirm content has embeddings

#### Slow Search Performance
**Problem**: Search takes too long
**Solutions**:
- Reduce search limit
- Use more specific queries
- Check system resources
- Consider content volume optimization

### Getting Help

If you encounter issues:
1. Check the [Troubleshooting Guide](../troubleshooting/)
2. Verify model configurations
3. Review search query syntax
4. Check system requirements

## Advanced Features

### Search Result Analysis
- Review relevance scores to understand match quality
- Use highlighted excerpts to verify result accuracy
- Follow source links for full context

### Batch Processing
- Use Ask feature for processing multiple related questions
- Save answers as notes for systematic knowledge building
- Create question templates for consistent analysis

### Integration Workflows
- Combine search with transformation features
- Use search results as input for AI analysis
- Create knowledge maps from search patterns

## Conclusion

Open Notebook's search capabilities provide both precision and discovery tools for your knowledge base. By combining traditional text search with modern vector search and AI-powered question answering, you can efficiently find information and generate insights from your content.

Remember to:
- Choose the right search type for your needs
- Configure appropriate AI models for Ask feature
- Save valuable results as notes
- Use iterative search strategies for best results
- Leverage both search types for comprehensive coverage

The search system grows more valuable as you add more content and develop better search strategies tailored to your specific knowledge domains.