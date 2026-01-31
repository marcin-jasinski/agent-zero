"""Knowledge Base Management Component for Agent Zero.

Implements document upload, indexing, and retrieval management.
Phase 5 Step 19.5: Enhanced with progress indicators and error visibility.
"""

import logging
import time
from typing import Optional

import streamlit as st

from src.config import get_config

logger = logging.getLogger(__name__)


def _get_ingestor():
    """Get or create cached document ingestor.
    
    Returns:
        Tuple of (DocumentIngestor instance or None, error_message or None)
    """
    if "document_ingestor" not in st.session_state:
        try:
            from src.core.ingest import DocumentIngestor
            from src.services.ollama_client import OllamaClient
            from src.services.qdrant_client import QdrantVectorClient
            from src.services.meilisearch_client import MeilisearchClient
            
            ollama = OllamaClient()
            if not ollama.is_healthy():
                return None, "Ollama service is not responding"
            
            qdrant = QdrantVectorClient()
            if not qdrant.is_healthy():
                return None, "Qdrant service is not responding"
            
            meilisearch = MeilisearchClient()
            if not meilisearch.is_healthy():
                return None, "Meilisearch service is not responding"
            
            st.session_state.document_ingestor = DocumentIngestor(
                ollama_client=ollama,
                qdrant_client=qdrant,
                meilisearch_client=meilisearch,
            )
            st.session_state.ingestor_error = None
        except Exception as e:
            logger.error(f"Failed to initialize document ingestor: {e}")
            st.session_state.document_ingestor = None
            st.session_state.ingestor_error = str(e)
    
    return st.session_state.get("document_ingestor"), st.session_state.get("ingestor_error")


def _get_retrieval_engine():
    """Get or create cached retrieval engine.
    
    Returns:
        Tuple of (RetrievalEngine instance or None, error_message or None)
    """
    if "retrieval_engine" not in st.session_state:
        try:
            from src.core.retrieval import RetrievalEngine
            from src.services.ollama_client import OllamaClient
            from src.services.qdrant_client import QdrantVectorClient
            from src.services.meilisearch_client import MeilisearchClient
            
            ollama = OllamaClient()
            if not ollama.is_healthy():
                return None, "Ollama service is not responding"
            
            qdrant = QdrantVectorClient()
            if not qdrant.is_healthy():
                return None, "Qdrant service is not responding"
            
            meilisearch = MeilisearchClient()
            if not meilisearch.is_healthy():
                return None, "Meilisearch service is not responding"
            
            st.session_state.retrieval_engine = RetrievalEngine(
                ollama_client=ollama,
                qdrant_client=qdrant,
                meilisearch_client=meilisearch,
            )
            st.session_state.retrieval_error = None
        except Exception as e:
            logger.error(f"Failed to initialize retrieval engine: {e}")
            st.session_state.retrieval_engine = None
            st.session_state.retrieval_error = str(e)
    
    return st.session_state.get("retrieval_engine"), st.session_state.get("retrieval_error")


def initialize_kb_session() -> None:
    """Initialize knowledge base session state variables."""
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "kb_last_error" not in st.session_state:
        st.session_state.kb_last_error = None


def _render_service_error(error_msg: str, service_hint: str) -> None:
    """Render a standardized service error message with troubleshooting hints.
    
    Args:
        error_msg: The error message to display
        service_hint: Hint about which service to check
    """
    st.error(f"Error: {error_msg}")
    st.info(f"""
**Troubleshooting Steps:**
1. Check if services are running: `docker-compose ps`
2. Start services if needed: `docker-compose up -d`
3. Check service logs: `docker-compose logs {service_hint}`
4. Verify port availability (no conflicts)
    """)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Retry", key=f"retry_{service_hint}"):
            # Clear cached services to force reconnection
            for key in ["document_ingestor", "retrieval_engine", "ingestor_error", "retrieval_error"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


def render_knowledge_base() -> None:
    """Render the knowledge base component.

    Allows users to upload documents, view indexed documents,
    and manage the knowledge base.
    """
    st.header("Knowledge Base Management")

    # Initialize session state
    initialize_kb_session()

    # Create tabs for KB management
    kb_tab1, kb_tab2, kb_tab3 = st.tabs(["Upload", "Documents", "Search"])

    with kb_tab1:
        st.subheader("Upload Documents")

        st.write("Upload PDF, TXT, or Markdown files to add them to your knowledge base.")

        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "md"],
            accept_multiple_files=False,
        )

        if uploaded_file:
            st.info(f"File: {uploaded_file.name} ({uploaded_file.size} bytes)")

            col1, col2 = st.columns(2)

            with col1:
                chunk_size = st.number_input(
                    "Chunk size (characters):",
                    min_value=100,
                    max_value=4000,
                    value=500,
                )

            with col2:
                overlap = st.number_input(
                    "Chunk overlap (characters):",
                    min_value=0,
                    max_value=1000,
                    value=50,
                )

            if st.button("Index Document", use_container_width=True):
                ingestor, error = _get_ingestor()
                
                if ingestor is None:
                    _render_service_error(
                        error or "Document ingestion service unavailable",
                        "ollama qdrant meilisearch"
                    )
                else:
                    # Create a progress container
                    progress_container = st.empty()
                    status_container = st.empty()
                    
                    with progress_container.container():
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # Step 1: Read file
                            status_text.text("Reading file...")
                            progress_bar.progress(10)
                            file_bytes = uploaded_file.read()
                            time.sleep(0.2)  # Brief pause for UX
                            
                            # Step 2: Parse content
                            status_text.text("Parsing document content...")
                            progress_bar.progress(25)
                            file_ext = uploaded_file.name.lower().split(".")[-1]
                            time.sleep(0.2)
                            
                            # Step 3: Chunk and embed
                            status_text.text("Chunking document and generating embeddings...")
                            progress_bar.progress(40)
                            
                            # Step 4: Process based on file type
                            if file_ext == "pdf":
                                result = ingestor.ingest_pdf_bytes(
                                    file_bytes, 
                                    uploaded_file.name,
                                    chunk_size=int(chunk_size),
                                    chunk_overlap=int(overlap),
                                )
                            else:
                                # For text/markdown, decode and ingest
                                text_content = file_bytes.decode("utf-8")
                                result = ingestor.ingest_text(
                                    text_content,
                                    uploaded_file.name,
                                    chunk_size=int(chunk_size),
                                    chunk_overlap=int(overlap),
                                )
                            
                            # Step 5: Indexing
                            status_text.text("Indexing in vector database...")
                            progress_bar.progress(80)
                            time.sleep(0.2)
                            
                            # Complete
                            progress_bar.progress(100)
                            status_text.text("Complete!")
                            time.sleep(0.3)
                            
                            if result.success:
                                st.session_state.documents.append({
                                    "filename": uploaded_file.name,
                                    "size": uploaded_file.size,
                                    "status": "indexed",
                                    "chunks": result.chunks_count,
                                    "document_id": result.document_id,
                                })
                                st.session_state.kb_last_error = None
                                progress_container.empty()
                                st.success(f"Document '{uploaded_file.name}' indexed successfully! ({result.chunks_count} chunks in {result.duration_seconds:.1f}s)")
                                st.balloons()
                                st.rerun()
                            else:
                                progress_container.empty()
                                st.error(f"Failed to index document: {result.error}")
                                st.session_state.kb_last_error = result.error
                                
                        except UnicodeDecodeError as e:
                            progress_container.empty()
                            st.error("Failed to read file: Invalid text encoding. Please ensure the file is UTF-8 encoded.")
                            logger.error(f"Unicode decode error: {e}")
                        except Exception as e:
                            progress_container.empty()
                            logger.error(f"Document indexing error: {e}", exc_info=True)
                            st.error(f"Error during indexing: {str(e)}")
                            st.info("Check the Logs tab for more details")

    with kb_tab2:
        st.subheader("Indexed Documents")

        if st.session_state.documents:
            import pandas as pd

            df = pd.DataFrame(st.session_state.documents)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Delete document option
            st.divider()
            col1, col2 = st.columns([3, 1])

            with col1:
                doc_to_delete = st.selectbox(
                    "Select document to delete:",
                    [doc["filename"] for doc in st.session_state.documents],
                    label_visibility="collapsed",
                )

            with col2:
                if st.button("Delete"):
                    st.session_state.documents = [
                        doc for doc in st.session_state.documents if doc["filename"] != doc_to_delete
                    ]
                    st.success("Document deleted!")
                    st.rerun()
        else:
            st.info("No documents indexed yet. Upload a document to get started.")

    with kb_tab3:
        st.subheader("Search Knowledge Base")

        search_query = st.text_input(
            "Search query:",
            placeholder="Enter keywords or a question...",
        )

        search_type = st.radio(
            "Search type:",
            ["Semantic", "Keyword", "Hybrid"],
            horizontal=True,
        )

        if search_query:
            if st.button("Search", use_container_width=True):
                retrieval, error = _get_retrieval_engine()
                
                if retrieval is None:
                    _render_service_error(
                        error or "Retrieval service unavailable",
                        "ollama qdrant meilisearch"
                    )
                else:
                    progress_container = st.empty()
                    
                    with progress_container.container():
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            status_text.text("Searching knowledge base...")
                            progress_bar.progress(30)
                            
                            # Map search type to retrieval parameter
                            use_hybrid = search_type == "Hybrid"
                            
                            status_text.text(f"Running {search_type.lower()} search...")
                            progress_bar.progress(60)
                            
                            if search_type == "Keyword":
                                results = retrieval._keyword_search(search_query, top_k=5)
                            else:
                                results = retrieval.retrieve_relevant_docs(
                                    search_query, 
                                    top_k=5, 
                                    hybrid=use_hybrid
                                )
                            
                            progress_bar.progress(100)
                            status_text.text("Search complete!")
                            time.sleep(0.2)
                            progress_container.empty()
                            
                            if results:
                                st.success(f"Found {len(results)} result(s)")
                                for i, result in enumerate(results):
                                    with st.expander(
                                        f"Result {i+1}: {result.source} (Score: {result.score:.3f})", 
                                        expanded=(i == 0)
                                    ):
                                        st.markdown(f"**Search type:** {result.search_type}")
                                        st.markdown(f"**Score:** {result.score:.4f}")
                                        st.markdown(f"**Source:** {result.source}")
                                        st.markdown("**Content:**")
                                        st.text(result.content[:500] + "..." if len(result.content) > 500 else result.content)
                            else:
                                st.info("No results found for your query.")
                                st.markdown("""
**Tips to improve search results:**
- Try different keywords or phrases
- Upload more documents to the Knowledge Base
- Use Hybrid search for best results
- Check if documents were indexed successfully
                                """)
                        except Exception as e:
                            progress_container.empty()
                            logger.error(f"Search error: {e}", exc_info=True)
                            st.error(f"Search failed: {str(e)}")
                            st.info("Make sure you have indexed some documents first")
        else:
            st.info("Enter a search query to find relevant documents from your knowledge base.")
