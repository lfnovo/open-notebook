import asyncio
import time
from api.client import APIClient

async def main():
    print("Initializing APIClient...")
    client = APIClient(base_url="http://localhost:5055")
    
    # 1. Create a notebook for the exams
    print("Creating Notebook...")
    notebook = client.create_notebook(
        name="Mega Examination Database",
        description="A notebook containing 300 exam-related files for testing the Study Guide compiler."
    )
    notebook_id = notebook["id"]
    print(f"Created Notebook with ID: {notebook_id}")
    
    # 2. Generate and upload 300 mock exam files
    print("Beginning upload of 300 mock files...")
    start_time = time.time()
    
    # We upload in batches to avoid overwhelming the server, but open-notebook's 
    # API processes them synchronously if we wait for the response. 
    # Let's do it concurrently in batches of 10.
    
    def upload_file(i):
        # We run the synchronous client in a thread or just use it if it's fast enough.
        # Since client.create_source uses requests, it is synchronous.
        try:
            content = f"This is examination document number {i}. It covers topic {i} in the syllabus. It includes 10 multiple choice questions and 2 essay topics related to advanced computer science topic {i}."
            client.create_source(
                source_type="text",
                notebook_id=notebook_id,
                title=f"CS_Exam_Topic_{i}.txt",
                content=content,
                async_processing=True # Tell backend to process it asynchronously to speed up API response
            )
            if i % 20 == 0:
                print(f"Uploaded file {i}/300...")
        except Exception as e:
            print(f"Failed to upload file {i}: {e}")

    # Use sequential uploading to avoid SurrealDB transaction conflicts
    for i in range(1, 301):
        upload_file(i)
    
    end_time = time.time()
    print(f"Successfully uploaded 300 files in {end_time - start_time:.2f} seconds!")

if __name__ == "__main__":
    asyncio.run(main())
