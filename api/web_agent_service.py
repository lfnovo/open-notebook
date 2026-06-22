import os
from typing import List, Dict, Any
from pydantic import BaseModel
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchResults
from duckduckgo_search import DDGS

# Define the models we want to use. We can pull the API key from environment
def get_nvidia_llm():
    # Make sure NVIDIA_API_KEY is in the environment
    return ChatNVIDIA(model="meta/llama3-70b-instruct")

class StudyGuideRequest(BaseModel):
    notebook_id: str

class StudyGuideResponse(BaseModel):
    notebook_id: str
    markdown_content: str
    references: List[str]

async def compile_study_guide(request: StudyGuideRequest) -> StudyGuideResponse:
    from api.sources_service import sources_service
    llm = get_nvidia_llm()
    
    # Fetch all sources for the notebook
    sources = sources_service.get_all_sources(notebook_id=request.notebook_id)
    combined_source_text = "\n\n".join([s.full_text for s in sources if s.full_text])
    
    # 1. Extract Topics
    topic_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert curriculum designer. Extract the 3 most important topics from the following text for a comprehensive web search. Output ONLY the 3 topics separated by commas, nothing else."),
        ("user", "{text}")
    ])
    
    chain = topic_prompt | llm
    topics_response = await chain.ainvoke({"text": combined_source_text[:4000]}) # limit text size for extraction
    topics = [t.strip() for t in topics_response.content.split(',')]
    
    # 2. Web Search
    search_results = []
    references = []
    
    with DDGS() as ddgs:
        for topic in topics:
            if not topic: continue
            try:
                results = list(ddgs.text(f"study guide {topic}", max_results=3))
                for res in results:
                    search_results.append(f"Title: {res['title']}\nBody: {res['body']}\nLink: {res['href']}")
                    references.append(res['href'])
            except Exception as e:
                print(f"Search failed for {topic}: {e}")
                
    combined_search_context = "\n\n".join(search_results)
    
    # 3. Synthesize
    synthesis_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert AI Exam Compiler. Your job is to create a comprehensive, well-structured Markdown study guide. Combine the ground-truth information from the provided source text with the supplementary web search results. Use markdown headers, bullet points, and include references to the web links where appropriate."),
        ("user", "SOURCE TEXT (from user PDFs):\n{source_text}\n\n---\n\nSUPPLEMENTARY WEB SEARCH RESULTS:\n{web_results}\n\n---\n\nGenerate the complete Markdown Study Guide now:")
    ])
    
    synth_chain = synthesis_prompt | llm
    final_guide_response = await synth_chain.ainvoke({
        "source_text": combined_source_text[:10000], # Keep context window manageable
        "web_results": combined_search_context
    })
    
    return StudyGuideResponse(
        notebook_id=request.notebook_id,
        markdown_content=final_guide_response.content,
        references=list(set(references))
    )
