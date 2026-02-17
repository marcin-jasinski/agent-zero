"""Qdrant Manager Dashboard Component (Phase 4b Step 18).

Provides UI for managing Qdrant vector database:
- View all collections with stats
- Semantic search interface
- Create/delete collections
- Collection details viewer

Design Reference: DASHBOARD_DESIGN.md § "Qdrant Manager Tab"
"""

import logging
from typing import Any, Optional

import streamlit as st

from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantVectorClient

logger = logging.getLogger(__name__)


def initialize_qdrant_session() -> None:
    """Initialize session state for Qdrant dashboard."""
    if "qdrant_search_results" not in st.session_state:
        st.session_state.qdrant_search_results = []
    if "qdrant_selected_collection" not in st.session_state:
        st.session_state.qdrant_selected_collection = None
    if "qdrant_show_create_form" not in st.session_state:
        st.session_state.qdrant_show_create_form = False


@st.cache_data(ttl=300)
def get_collections_cached() -> list[dict[str, Any]]:
    """Get list of collections with 5-minute cache.
    
    Returns:
        List of collection dicts with metadata
    """
    try:
        qdrant = QdrantVectorClient()
        return qdrant.list_collections()
    except Exception as e:
        logger.error(f"Failed to fetch collections: {e}")
        return []


@st.cache_data(ttl=60)
def search_collection_cached(
    query: str,
    collection: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """Search collection with 1-minute cache.
    
    Args:
        query: Text query
        collection: Collection name
        top_k: Number of results
        
    Returns:
        List of search results
    """
    try:
        qdrant = QdrantVectorClient()
        ollama = OllamaClient()
        return qdrant.search_by_text(
            query=query,
            collection=collection,
            top_k=top_k,
            ollama_client=ollama,
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def render_collections_overview() -> None:
    """Render collections overview section."""
    st.subheader("Collections Overview")
    
    # Refresh button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Refresh", key="qdrant_refresh", use_container_width=True):
            get_collections_cached.clear()
            st.rerun()
    
    # Get collections
    collections = get_collections_cached()
    
    if not collections:
        st.info("No collections found. Create your first collection below.")
        return
    
    # Display collections in expandable cards
    for collection in collections:
        with st.expander(f"{collection['name']}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Vectors", f"{collection['vectors_count']:,}")
            with col2:
                st.metric("Points", f"{collection['points_count']:,}")
            with col3:
                # Get detailed stats
                try:
                    qdrant = QdrantVectorClient()
                    stats = qdrant.get_collection_stats(collection['name'])
                    if stats:
                        st.metric("Dimensions", stats['vector_size'])
                        st.caption(f"Distance: {stats['distance_metric']}")
                        st.caption(f"Status: {stats['status']}")
                except Exception as e:
                    logger.error(f"Failed to get stats for {collection['name']}: {e}")
                    st.caption("Stats unavailable")
            
            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "Search",
                    key=f"search_{collection['name']}",
                    use_container_width=True,
                ):
                    st.session_state.qdrant_selected_collection = collection['name']
                    st.rerun()
            
            with col2:
                if st.button(
                    "Delete",
                    key=f"delete_{collection['name']}",
                    use_container_width=True,
                    type="secondary",
                ):
                    # Show confirmation
                    if st.session_state.get(f"confirm_delete_{collection['name']}", False):
                        # Confirmed - delete
                        try:
                            qdrant = QdrantVectorClient()
                            success, message = qdrant.delete_collection_ui(collection['name'])
                            if success:
                                st.success(message)
                                get_collections_cached.clear()
                                st.session_state[f"confirm_delete_{collection['name']}"] = False
                                st.rerun()
                            else:
                                st.error(message)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                    else:
                        # Request confirmation
                        st.session_state[f"confirm_delete_{collection['name']}"] = True
                        st.warning(f"Click 'Delete' again to confirm deletion of '{collection['name']}'")
                        st.rerun()


def render_create_collection_form() -> None:
    """Render create collection form."""
    st.subheader("Create New Collection")
    
    with st.form("create_collection_form"):
        name = st.text_input(
            "Collection Name",
            placeholder="my_collection",
            help="Alphanumeric characters, underscores, and hyphens only",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            vector_size = st.number_input(
                "Vector Size",
                min_value=1,
                max_value=2048,
                value=768,
                step=1,
                help="Embedding dimensionality (must match your model)",
            )
        
        with col2:
            distance = st.selectbox(
                "Distance Metric",
                options=["Cosine", "Euclid", "Dot"],
                index=0,
                help="Similarity metric for vector search",
            )
        
        submitted = st.form_submit_button("Create Collection", use_container_width=True)
        
        if submitted:
            try:
                qdrant = QdrantVectorClient()
                success, message = qdrant.create_collection_ui(
                    name=name,
                    vector_size=vector_size,
                    distance=distance,
                )
                
                if success:
                    st.success(message)
                    get_collections_cached.clear()
                    st.session_state.qdrant_show_create_form = False
                    st.rerun()
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error creating collection: {str(e)}")


def render_search_interface() -> None:
    """Render semantic search interface."""
    st.subheader("Semantic Search")
    
    # Get available collections
    collections = get_collections_cached()
    
    if not collections:
        st.info("No collections available for search. Create a collection first.")
        return
    
    collection_names = [c['name'] for c in collections]
    
    # Pre-select collection if set
    default_index = 0
    if st.session_state.qdrant_selected_collection in collection_names:
        default_index = collection_names.index(st.session_state.qdrant_selected_collection)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_collection = st.selectbox(
            "Collection",
            options=collection_names,
            index=default_index,
            key="search_collection",
        )
    
    with col2:
        top_k = st.slider(
            "Top K",
            min_value=1,
            max_value=20,
            value=5,
            help="Number of results to return",
        )
    
    # Search query
    query = st.text_area(
        "Search Query",
        placeholder="Enter your search query...",
        height=100,
        key="search_query",
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_button = st.button("Search", use_container_width=True, type="primary")
    
    with col2:
        if st.button("Clear", use_container_width=True):
            st.session_state.qdrant_search_results = []
            st.rerun()
    
    # Perform search
    if search_button:
        if not query or not query.strip():
            st.warning("Please enter a search query")
        else:
            with st.spinner("Searching..."):
                try:
                    results = search_collection_cached(
                        query=query.strip(),
                        collection=selected_collection,
                        top_k=top_k,
                    )
                    st.session_state.qdrant_search_results = results
                    st.rerun()
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")
                    logger.error(f"Search error: {e}", exc_info=True)
    
    # Display results
    results = st.session_state.qdrant_search_results
    
    if results:
        st.divider()
        st.write(f"**Results:** {len(results)} matches")
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            content = result.get('content', '')
            source = result.get('source', 'Unknown')
            chunk_index = result.get('chunk_index', 0)
            
            # Color code by score
            if score >= 0.8:
                score_color = "[HIGH]"
            elif score >= 0.6:
                score_color = "[MED]"
            else:
                score_color = "[LOW]"
            
            with st.expander(f"{score_color} **{i}.** Score: {score:.4f} | {source} (chunk {chunk_index})"):
                st.write(content[:500] + ("..." if len(content) > 500 else ""))
                
                # Show full content button
                if len(content) > 500:
                    if st.button(f"Show full content", key=f"show_full_{i}"):
                        st.text(content)


def render_qdrant_dashboard() -> None:
    """Main render function for Qdrant Manager dashboard.
    
    Displays:
    - Collections overview with stats
    - Create collection form
    - Semantic search interface
    """
    # Initialize session state
    initialize_qdrant_session()
    
    # Header
    st.header("Qdrant Manager")
    st.caption("Vector Database Management Interface")
    
    # Check Qdrant health
    try:
        qdrant = QdrantVectorClient()
        if not qdrant.is_healthy():
            st.error("Qdrant service is not responding. Please check your configuration.")
            return
    except Exception as e:
        st.error(f"Failed to connect to Qdrant: {str(e)}")
        return
    
    st.success("Connected to Qdrant")
    st.divider()
    
    # Collections Overview
    render_collections_overview()
    
    st.divider()
    
    # Create Collection Toggle
    if st.button(
        "Create New Collection" if not st.session_state.qdrant_show_create_form else "Cancel",
        key="toggle_create_form",
    ):
        st.session_state.qdrant_show_create_form = not st.session_state.qdrant_show_create_form
        st.rerun()
    
    if st.session_state.qdrant_show_create_form:
        render_create_collection_form()
    
    st.divider()
    
    # Search Interface
    render_search_interface()
