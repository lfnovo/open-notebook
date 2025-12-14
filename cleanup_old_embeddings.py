#!/usr/bin/env python3
"""
Clean up old embed_chunk jobs and report which sources they belonged to.
"""
import asyncio
from open_notebook.database.repository import repo_query, parse_record_ids

async def main():
    print("Querying for old embed_chunk jobs...")
    
    # Get all pending/running/failed embed_chunk jobs
    result = await repo_query(
        """
        SELECT id, input, status, created FROM command 
        WHERE command = 'embed_chunk' 
        AND status IN ['pending', 'running', 'failed']
        ORDER BY created DESC
        """,
        {}
    )
    
    if not result:
        print("✓ No stuck embed_chunk jobs found!")
        return
    
    print(f"Found {len(result)} old embed_chunk jobs\n")
    
    # Group by source_id and get unique sources
    source_jobs = {}
    for job in result:
        if isinstance(job, dict):
            source_id = job.get("input", {}).get("source_id") if isinstance(job.get("input"), dict) else None
            status = job.get("status", "unknown")
            
            if source_id:
                if source_id not in source_jobs:
                    source_jobs[source_id] = []
                source_jobs[source_id].append({
                    "job_id": str(job.get("id", "")),
                    "status": status,
                    "created": job.get("created"),
                    "chunk_index": job.get("input", {}).get("chunk_index") if isinstance(job.get("input"), dict) else None
                })
    
    print(f"Jobs grouped by {len(source_jobs)} unique sources:\n")
    
    # Look up source titles
    from open_notebook.domain.notebook import Source
    
    affected_sources = []
    for source_id in sorted(source_jobs.keys()):
        jobs = source_jobs[source_id]
        try:
            source = await Source.get(source_id)
            title = source.title if source else f"<Unknown: {source_id}>"
        except Exception as e:
            title = f"<Error: {e}>"
        
        status_counts = {}
        for job in jobs:
            s = job["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        
        status_str = ", ".join([f"{count} {status}" for status, count in status_counts.items()])
        print(f"  📄 {title}")
        print(f"     Source ID: {source_id}")
        print(f"     Jobs: {status_str}\n")
        affected_sources.append((title, source_id))
    
    # Delete all embed_chunk jobs
    print(f"Deleting {len(result)} old embed_chunk jobs...")
    delete_result = await repo_query(
        """
        DELETE command WHERE command = 'embed_chunk'
        """,
        {}
    )
    
    deleted_count = len(delete_result) if delete_result else 0
    print(f"\n✓ Deleted {deleted_count} embed_chunk jobs\n")
    
    if affected_sources:
        print("Sources to re-upload for fresh vectorization:")
        for title, source_id in affected_sources:
            print(f"  • {title} ({source_id})")
    
    print("\nYou can now re-upload these sources to start fresh vectorization with the batch approach.")

if __name__ == "__main__":
    asyncio.run(main())
