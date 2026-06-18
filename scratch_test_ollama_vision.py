import asyncio
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage
import base64

async def main():
    llm = ChatOllama(model="llama3.2-vision", base_url="http://localhost:11434")
    
    # Create a tiny 1x1 white jpeg in base64
    b64_image = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Describe this image"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
            },
        ]
    )
    
    print("Invoking...")
    try:
        response = await llm.ainvoke([message])
        print("Response:", repr(response.content))
    except Exception as e:
        print("Error:", str(e))

asyncio.run(main())
