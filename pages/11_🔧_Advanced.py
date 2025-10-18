import time

import streamlit as st
from loguru import logger

from api.client import api_client
from pages.stream_app.utils import setup_page

setup_page("🔧 Advanced")

st.header("🔧 Advanced")

# =============================================================================
# Rebuild Embeddings Section
# =============================================================================

with st.container(border=True):
    st.markdown("### 🔄 Rebuild Embeddings")
    st.caption(
        "Rebuild vector embeddings for your content. Use this when switching embedding models "
        "or fixing corrupted embeddings."
    )

    col1, col2 = st.columns(2)

    with col1:
        rebuild_mode = st.selectbox(
            "Rebuild Mode",
            ["existing", "all"],
            index=0,
            help="Choose which items to rebuild",
        )

        with st.expander("Help me choose"):
            st.markdown("""
**Existing**: Re-embed only items that already have embeddings
- Use this when switching embedding models
- Faster, processes only embedded content
- Maintains your current embedded item list

**All**: Re-embed existing items + create embeddings for items without any
- Use this to embed everything in your database
- Slower, processes all content
- Finds and embeds previously un-embedded items
""")

    with col2:
        st.markdown("**Include in Rebuild:**")
        include_sources = st.checkbox("Sources", value=True, help="Include source documents")
        include_notes = st.checkbox("Notes", value=True, help="Include notes")
        include_insights = st.checkbox("Insights", value=True, help="Include source insights")

    # Check if at least one type is selected
    if not (include_sources or include_notes or include_insights):
        st.warning("⚠️ Please select at least one item type to rebuild")

    # Rebuild button
    if st.button("🚀 Start Rebuild", type="primary", disabled=not (include_sources or include_notes or include_insights)):
        with st.spinner("Starting rebuild..."):
            try:
                result = api_client.rebuild_embeddings(
                    mode=rebuild_mode,
                    include_sources=include_sources,
                    include_notes=include_notes,
                    include_insights=include_insights
                )

                if isinstance(result, dict):
                    command_id = result.get("command_id")
                    estimated_items = result.get("estimated_items", 0)
                else:
                    raise ValueError("Invalid result from rebuild_embeddings")

                # Store command ID in session state for status tracking
                st.session_state["rebuild_command_id"] = command_id
                st.session_state["rebuild_start_time"] = time.time()

                st.success(f"✅ Rebuild started! Processing approximately {estimated_items} items.")
                st.info(f"Command ID: `{command_id}`")
                st.rerun()

            except Exception as e:
                logger.error(f"Failed to start rebuild: {e}")
                st.error(f"❌ Failed to start rebuild: {str(e)}")

# =============================================================================
# Rebuild Status Section
# =============================================================================

# Show status if a rebuild is in progress
if "rebuild_command_id" in st.session_state:
    command_id = st.session_state["rebuild_command_id"]

    with st.container(border=True):
        st.markdown("### 📊 Rebuild Status")

        # Create placeholder for dynamic updates
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        stats_placeholder = st.empty()

        try:
            status_result = api_client.get_rebuild_status(command_id)

            if isinstance(status_result, dict):
                status = status_result.get("status")
                progress = status_result.get("progress")
                stats = status_result.get("stats")
                error_message = status_result.get("error_message")
                started_at = status_result.get("started_at")
                completed_at = status_result.get("completed_at")
            else:
                status = None
                progress = None
                stats = None
                error_message = None
                started_at = None
                completed_at = None

            # Calculate elapsed time
            if "rebuild_start_time" in st.session_state:
                elapsed = time.time() - st.session_state["rebuild_start_time"]
                elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            else:
                elapsed_str = "Unknown"

            # Show status
            if status == "queued":
                status_placeholder.info("⏳ **Status**: Queued (waiting to start)")
            elif status == "running":
                status_placeholder.info(f"⚙️ **Status**: Running... (Elapsed: {elapsed_str})")

                # Auto-refresh every 5 seconds if running
                time.sleep(5)
                st.rerun()

            elif status == "completed":
                status_placeholder.success("✅ **Status**: Completed!")

                # Clear session state
                if "rebuild_command_id" in st.session_state:
                    del st.session_state["rebuild_command_id"]
                if "rebuild_start_time" in st.session_state:
                    del st.session_state["rebuild_start_time"]

            elif status == "failed":
                status_placeholder.error("❌ **Status**: Failed")
                if error_message:
                    st.error(f"Error: {error_message}")

                # Clear session state
                if "rebuild_command_id" in st.session_state:
                    del st.session_state["rebuild_command_id"]
                if "rebuild_start_time" in st.session_state:
                    del st.session_state["rebuild_start_time"]

            # Show progress if available
            if progress:
                total = progress.get("total_items", 0)
                processed = progress.get("processed_items", 0)
                failed = progress.get("failed_items", 0)

                if total > 0:
                    progress_pct = (processed / total) * 100
                    progress_placeholder.progress(
                        progress_pct / 100,
                        text=f"Progress: {processed}/{total} items ({progress_pct:.1f}%)"
                    )

                    if failed > 0:
                        st.warning(f"⚠️ {failed} items failed to process")

            # Show stats if available
            if stats:
                with stats_placeholder.container():
                    st.markdown("#### Processing Statistics")
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Sources", stats.get("sources_processed", 0))
                    with col2:
                        st.metric("Notes", stats.get("notes_processed", 0))
                    with col3:
                        st.metric("Insights", stats.get("insights_processed", 0))
                    with col4:
                        processing_time = stats.get("processing_time", 0)
                        st.metric("Time", f"{processing_time:.1f}s")

            # Show timestamps
            if started_at or completed_at:
                st.markdown("---")
                col1, col2 = st.columns(2)
                if started_at:
                    with col1:
                        st.caption(f"Started: {started_at}")
                if completed_at:
                    with col2:
                        st.caption(f"Completed: {completed_at}")

        except Exception as e:
            logger.error(f"Failed to get rebuild status: {e}")
            status_placeholder.error(f"❌ Failed to get status: {str(e)}")

            # Clear session state on error
            if "rebuild_command_id" in st.session_state:
                del st.session_state["rebuild_command_id"]
            if "rebuild_start_time" in st.session_state:
                del st.session_state["rebuild_start_time"]

# =============================================================================
# Additional Info Section
# =============================================================================

with st.container(border=True):
    st.markdown("### ℹ️ About Embedding Rebuilds")

    with st.expander("When should I rebuild embeddings?"):
        st.markdown("""
**You should rebuild embeddings when:**

1. **Switching embedding models**: If you change from one embedding model to another (e.g., from OpenAI to Google Gemini),
   you need to rebuild all embeddings to ensure consistency.

2. **Upgrading embedding model versions**: When updating to a newer version of your embedding model,
   rebuild to take advantage of improvements.

3. **Fixing corrupted embeddings**: If you suspect some embeddings are corrupted or missing,
   rebuilding can restore them.

4. **After bulk imports**: If you imported content without embeddings, use "All" mode to embed everything.
""")

    with st.expander("How long does rebuilding take?"):
        st.markdown("""
**Processing time depends on:**

- Number of items to process
- Embedding model speed
- API rate limits (for cloud providers)
- System resources

**Typical rates:**

- **Local models** (Ollama): Very fast, limited only by hardware
- **Cloud APIs** (OpenAI, Google): Moderate speed, may hit rate limits with large datasets
- **Sources**: Slower than notes/insights (creates multiple chunks per source)

**Example**: Rebuilding 200 items might take 2-5 minutes with cloud APIs, or under 1 minute with local models.
""")

    with st.expander("Is it safe to rebuild while using the app?"):
        st.markdown("""
**Yes, rebuilding is safe!** The rebuild process:

✅ **Is idempotent**: Running multiple times produces the same result
✅ **Doesn't delete content**: Only replaces embeddings
✅ **Can be run anytime**: No need to stop other operations
✅ **Handles errors gracefully**: Failed items are logged and skipped

⚠️ **However**: Very large rebuilds (1000s of items) may temporarily slow down searches while processing.
""")

