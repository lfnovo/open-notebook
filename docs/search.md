# Integrated Search Engines

When it comes to managing information and learning, search plays a big role. Being able to find useful information and put it to use is one fhe most fundamental aspects of any succesfull knowledge strategy. 

We help you do that in 2 ways:

## 1 - Search

Open Notebook comes equipped with built-in full-text and vector search capabilities, enabling you to quickly find the information you need. The full-text search lets you search across all your notes and documents, while vector search allows for more context-based and semantic retrieval. This dual search capability ensures that you can find specific details or broad concepts with ease, streamlining your research process and saving valuable time.

![Search](/assets/search.png)

## 2 - Ask your Knowledge Base

All your sources and notes are part of a huge knowledge source that you can tap into at any time. One of the most usefuls things to do with them is to have them available for the AI Assistant to query and ellaborate on.

With the Ask feature, you can define a question, selected the LLM models you'd like to process and just relax until they do all the work. 

The process happens as follows:

- AI will interpret your query and generate several searches to try to answer parts of it
- Each query will be processed and analyzed individually
- All queries are combined into one coherent answer. 

You can customize 3 models for processing the query:

| Provider | Highlights |
|------------|-----------|
| Query Strategy | Decides what to search for in order to reply. You should use a powerful model here like Claude Sonnet, GPT-4o, Llama 3.2, Gemini Pro or Grok |
| Individual Answer | Each query gets processed by its own AI model to generate a subpart of the answer. You can use cheaper/faster models here like gpt-4o-mini, Gemini Flash or Ollama models |
| Final Answer | This is the model that combines all individual answers into a single response. Use a powerful model here for best results. |

![Ask](/assets/ask.png)


### Citations

The answers will also include a link to the document where its facts came from, so can you check the reference of what's been presented. 

![Answer](/assets/ask_answer.png)


