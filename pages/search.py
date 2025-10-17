#!/usr/bin/env python3
"""
PostgreSQL Search Showcase Module
Demonstrates ILIKE, pg_trgm, and pgvector search capabilities
"""

import streamlit as st
import pandas as pd
import os
from db_utils import get_db_connection, get_postgres_config
from sqlalchemy import text

def show_search_page():
    """Display the search showcase page"""
    
    # Custom CSS for styling
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 1rem;
        }
        .section-divider {
            border-top: 2px solid #e1e5e9;
            margin: 2rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<h1 class="main-header">🔍 PostgreSQL Search Showcase</h1>', unsafe_allow_html=True)

    # Check PostgreSQL connection
    try:
        postgres_config = get_postgres_config()
        use_postgres = True
        st.success("✅ PostgreSQL connection available")
    except Exception as e:
        use_postgres = False
        st.error("❌ PostgreSQL connection not available")
        st.info("Make sure your PostgreSQL credentials are configured in `.streamlit/secrets.toml`")
        st.stop()

    if use_postgres:
        st.markdown("""
        **Discover the power of PostgreSQL search capabilities!** This demo showcases three different approaches to searching transaction data, 
        each building upon the previous to show the evolution from basic pattern matching to advanced semantic understanding.
        """)
        
        # Search method selector
        search_method = st.selectbox(
            "Choose Search Method:",
            ["ILIKE Pattern Matching", "pg_trgm Fuzzy Search", "pgvector Semantic Search"],
            help="Select different search approaches to see how they handle various queries"
        )
        
        # Search input
        search_query = st.text_input(
            "Enter your search query:",
            placeholder="Try searching for 'coffee', 'subscription', or 'grocery shopping'",
            help="Enter any term to search through transaction merchants and notes"
        )
        
        if search_query:
            # =============================================================================
            # ILIKE PATTERN MATCHING
            # =============================================================================
            if search_method == "ILIKE Pattern Matching":
                st.subheader("🔤 ILIKE Pattern Matching")
                st.info("**Basic SQL pattern matching** - Searches for exact substring matches (case-insensitive)")
                
                with st.expander("ℹ️ How ILIKE Works", expanded=False):
                    st.markdown("""
                    **ILIKE** is PostgreSQL's case-insensitive pattern matching operator:
                    - Searches for exact substring matches within text
                    - Uses wildcards: `%` (any characters) and `_` (single character)
                    - Fast for simple queries but limited flexibility
                    - Example: `merchant ILIKE '%coffee%'`
                    """)
                
                try:
                    with get_db_connection() as conn:
                        result = conn.execute(text("""
                            SELECT 
                                transaction_id,
                                merchant,
                                notes,
                                amount,
                                date,
                                category
                            FROM transactions 
                            WHERE (merchant ILIKE :query OR notes ILIKE :query)
                            AND status = 'approved'
                            ORDER BY date DESC
                            LIMIT 20
                        """), {"query": f"%{search_query}%"})
                        
                        results = result.fetchall()
                        
                        if results:
                            st.success(f"Found {len(results)} matches using ILIKE pattern matching")
                            
                            # Display results in a nice table
                            df = pd.DataFrame([
                                {
                                    'ID': r.transaction_id,
                                    'Date': r.date.strftime('%Y-%m-%d'),
                                    'Merchant': r.merchant,
                                    'Notes': r.notes,
                                    'Amount': f"${r.amount:.2f}",
                                    'Category': r.category
                                }
                                for r in results
                            ])
                            
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.warning("No matches found with ILIKE pattern matching")
                            st.info("💡 Try broader terms like 'food', 'shop', or 'service'")
                            
                except Exception as e:
                    st.error(f"Search error: {e}")
            
            # =============================================================================
            # PG_TRGM FUZZY SEARCH  
            # =============================================================================
            elif search_method == "pg_trgm Fuzzy Search":
                st.subheader("🎯 pg_trgm Fuzzy Search")
                st.info("**Trigram-based fuzzy matching** - Handles typos and similar words using similarity scoring")
                
                with st.expander("ℹ️ How pg_trgm Works", expanded=False):
                    st.markdown("""
                    **pg_trgm** (trigram extension) provides advanced text search:
                    - Breaks text into 3-character sequences (trigrams)
                    - Calculates similarity scores between strings
                    - Handles typos, abbreviations, and similar words
                    - Uses GIN/GiST indexes for fast performance
                    - Example: 'cofee' matches 'coffee', 'strbks' matches 'starbucks'
                    """)
                
                # Check if pg_trgm extension exists
                try:
                    with get_db_connection() as conn:
                        # Check for extension
                        ext_check = conn.execute(text("""
                            SELECT EXISTS(
                                SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
                            ) as has_trgm
                        """)).fetchone()
                        
                        if not ext_check.has_trgm:
                            st.warning("⚠️ pg_trgm extension not installed")
                            st.info("Install with: `CREATE EXTENSION pg_trgm;`")
                            st.info("For now, falling back to enhanced ILIKE search...")
                            
                            # Fallback to enhanced ILIKE
                            result = conn.execute(text("""
                                SELECT 
                                    transaction_id,
                                    merchant,
                                    notes,
                                    amount,
                                    date,
                                    category
                                FROM transactions 
                                WHERE (merchant ILIKE :query OR notes ILIKE :query)
                                AND status = 'approved'
                                ORDER BY date DESC
                                LIMIT 20
                            """), {"query": f"%{search_query}%"})
                        else:
                            # Use pg_trgm similarity search
                            result = conn.execute(text("""
                                SELECT 
                                    transaction_id,
                                    merchant,
                                    notes,
                                    amount,
                                    date,
                                    category,
                                    GREATEST(
                                        similarity(merchant, :query),
                                        similarity(notes, :query)
                                    ) as similarity_score
                                FROM transactions 
                                WHERE (
                                    similarity(merchant, :query) > 0.1 OR
                                    similarity(notes, :query) > 0.1 OR
                                    notes ILIKE :ilike_query OR 
                                    merchant ILIKE :ilike_query
                                )
                                AND status = 'approved'
                                ORDER BY similarity_score DESC, date DESC
                                LIMIT 20
                            """), {
                                "query": search_query, 
                                "ilike_query": f"%{search_query}%"
                            })
                        
                        results = result.fetchall()
                        
                        if results:
                            st.success(f"Found {len(results)} matches using pg_trgm fuzzy search")
                            
                            # Display results with similarity scores if available
                            df_data = []
                            for r in results:
                                row = {
                                    'ID': r.transaction_id,
                                    'Date': r.date.strftime('%Y-%m-%d'),
                                    'Merchant': r.merchant,
                                    'Notes': r.notes,
                                    'Amount': f"${r.amount:.2f}",
                                    'Category': r.category
                                }
                                # Add similarity score if available
                                if hasattr(r, 'similarity_score') and r.similarity_score:
                                    row['Similarity'] = f"{r.similarity_score:.3f}"
                                df_data.append(row)
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(df, use_container_width=True)
                            
                            if 'Similarity' in df.columns:
                                st.caption("💡 Similarity scores show how closely results match your query")
                        else:
                            st.warning("No matches found with pg_trgm fuzzy search")
                            
                except Exception as e:
                    st.error(f"Search error: {e}")
            
            # =============================================================================
            # PGVECTOR SEMANTIC SEARCH
            # =============================================================================
            elif search_method == "pgvector Semantic Search":
                st.subheader("🧠 pgvector Semantic Search")
                st.info("**AI-powered semantic understanding** - Finds conceptually similar results using vector embeddings")
                
                with st.expander("ℹ️ How pgvector Works", expanded=False):
                    st.markdown("""
                    **pgvector** enables semantic search using AI embeddings:
                    - Converts text to high-dimensional vectors using AI models
                    - Finds semantically similar content, not just text matches
                    - Understands context and meaning, not just keywords
                    - Uses cosine similarity for relevance scoring
                    - Example: 'morning drink' finds 'coffee' and 'espresso'
                    """)
                
                # Check if pgvector extension exists
                try:
                    with get_db_connection() as conn:
                        ext_check = conn.execute(text("""
                            SELECT EXISTS(
                                SELECT 1 FROM pg_extension WHERE extname = 'vector'
                            ) as has_vector
                        """)).fetchone()
                        
                        if not ext_check.has_vector:
                            st.warning("⚠️ pgvector extension not installed")
                            st.info("Install with: `CREATE EXTENSION vector;`")
                            st.info("Run `python3 setup_embeddings.py` to set up semantic search")
                            st.stop()
                        
                        # Check if embeddings column exists and has data
                        embedding_check = conn.execute(text("""
                            SELECT 
                                EXISTS(
                                    SELECT 1 FROM information_schema.columns 
                                    WHERE table_name = 'transactions' 
                                    AND column_name = 'embedding'
                                ) as has_embedding_column,
                                (SELECT COUNT(*) FROM transactions WHERE embedding IS NOT NULL) as embedding_count
                        """)).fetchone()
                        
                        has_embeddings = embedding_check.has_embedding_column and embedding_check.embedding_count > 0
                        
                        if not has_embeddings:
                            st.warning("⚠️ No embeddings found in database")
                            st.info("**Setup Instructions:**")
                            st.code("""
# 1. Install OpenAI library
pip install openai

# 2. Add your OpenAI API key to .streamlit/secrets.toml:
[openai]
api_key = "sk-your-key-here"

# Or set as environment variable:
export OPENAI_API_KEY='your-key-here'

# 3. Run the embeddings setup
python3 setup_embeddings.py
                            """)
                            st.info("Get your API key from: https://platform.openai.com/api-keys")
                            
                            # Show simulated results as fallback
                            st.info("**For now, showing simulated semantic search results...**")
                            
                            # Simulate semantic search with enhanced keyword matching
                            semantic_terms = {
                                'coffee': ['starbucks', 'cafe', 'espresso', 'latte', 'cappuccino', 'brew'],
                                'food': ['restaurant', 'dining', 'grocery', 'meal', 'kitchen', 'cooking'],
                                'transport': ['uber', 'lyft', 'taxi', 'gas', 'fuel', 'parking'],
                                'shopping': ['store', 'retail', 'purchase', 'buy', 'market'],
                                'subscription': ['monthly', 'service', 'premium', 'plan', 'membership']
                            }
                            
                            # Find related terms
                            related_terms = [search_query.lower()]
                            for key, terms in semantic_terms.items():
                                if search_query.lower() in key or key in search_query.lower():
                                    related_terms.extend(terms)
                            
                            # Build query with related terms
                            ilike_conditions = " OR ".join([
                                f"(notes ILIKE '%{term}%' OR merchant ILIKE '%{term}%')"
                                for term in related_terms
                            ])
                            
                            result = conn.execute(text(f"""
                                SELECT 
                                    transaction_id,
                                    merchant,
                                    notes,
                                    amount,
                                    date,
                                    category
                                FROM transactions 
                                WHERE ({ilike_conditions})
                                AND status = 'approved'
                                ORDER BY date DESC
                                LIMIT 20
                            """))
                            
                            results = result.fetchall()
                            
                            if results:
                                st.success(f"Found {len(results)} simulated semantic matches")
                                
                                df = pd.DataFrame([
                                    {
                                        'ID': r.transaction_id,
                                        'Date': r.date.strftime('%Y-%m-%d'),
                                        'Merchant': r.merchant,
                                        'Notes': r.notes,
                                        'Amount': f"${r.amount:.2f}",
                                        'Category': r.category
                                    }
                                    for r in results
                                ])
                                
                                st.dataframe(df, use_container_width=True)
                                st.caption("🤖 Simulated semantic search (setup embeddings for real AI search)")
                            else:
                                st.warning("No simulated semantic matches found")
                            
                            st.stop()
                        
                        # We have real embeddings! Try to use OpenAI for query embedding
                        try:
                            import openai
                            
                            # Check for OpenAI API key - try secrets first, then environment
                            api_key = None
                            if hasattr(st, 'secrets') and 'openai' in st.secrets:
                                api_key = st.secrets.get('openai', {}).get('api_key')
                            if not api_key:
                                api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_KEY')
                            
                            if not api_key:
                                st.error("❌ OpenAI API key not found")
                                st.info("Add OpenAI API key to `.streamlit/secrets.toml` under `[openai]` section with key `api_key`, or set OPENAI_API_KEY environment variable")
                                st.code('''# Add to .streamlit/secrets.toml:
[openai]
api_key = "sk-your-key-here"''', language='toml')
                                st.stop()
                            
                            # Generate embedding for search query
                            with st.spinner("🧠 Generating semantic embedding..."):
                                client = openai.OpenAI(api_key=api_key)
                                response = client.embeddings.create(
                                    model="text-embedding-3-small",
                                    input=search_query.strip()
                                )
                                query_embedding = response.data[0].embedding
                            
                            # Perform semantic search using raw SQL - bypass SQLAlchemy text() issues
                            query_embedding_str = str(query_embedding)
                            
                            # Use raw connection execute to avoid parameter issues
                            raw_sql = """
                                SELECT 
                                    transaction_id,
                                    merchant,
                                    notes,
                                    amount,
                                    date,
                                    category,
                                    (1 - (embedding <=> %s::vector)) as similarity
                                FROM transactions 
                                WHERE embedding IS NOT NULL
                                  AND status = 'approved'
                                  AND (1 - (embedding <=> %s::vector)) > 0.3
                                ORDER BY embedding <=> %s::vector
                                LIMIT 20
                            """
                            
                            # Execute with raw connection
                            import psycopg2.extras
                            cursor = conn.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                            cursor.execute(raw_sql, (query_embedding_str, query_embedding_str, query_embedding_str))
                            results = cursor.fetchall()
                            cursor.close()
                            
                            if results:
                                st.success(f"🧠 Found {len(results)} semantically similar transactions using AI embeddings!")
                                
                                # Display with similarity scores
                                df_data = []
                                for r in results:
                                    df_data.append({
                                        'ID': r['transaction_id'],
                                        'Date': r['date'].strftime('%Y-%m-%d'),
                                        'Merchant': r['merchant'],
                                        'Notes': r['notes'],
                                        'Amount': f"${r['amount']:.2f}",
                                        'Category': r['category'],
                                        'Similarity': f"{r['similarity']:.3f}"
                                    })
                                
                                df = pd.DataFrame(df_data)
                                st.dataframe(df, use_container_width=True)
                                st.caption("🚀 Real AI semantic search using OpenAI embeddings and pgvector!")
                                
                                # Show embedding stats
                                st.info(f"📊 Database contains {embedding_check.embedding_count} transactions with embeddings")
                            else:
                                st.warning("No semantically similar transactions found (similarity > 0.3)")
                                st.info("Try broader terms or check if your data has relevant content")
                        
                        except ImportError:
                            st.error("❌ OpenAI library not installed")
                            st.info("Install with: `pip install openai`")
                        except Exception as embedding_error:
                            st.error(f"❌ Embedding generation error: {embedding_error}")
                            st.info("Check your OpenAI API key and internet connection")
                            
                except Exception as e:
                    st.error(f"Search error: {e}")
        
        # =============================================================================
        # SEARCH COMPARISON & INSIGHTS
        # =============================================================================
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.subheader("📊 Search Method Comparison")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🔤 ILIKE Pattern**
            - ✅ Simple & fast
            - ✅ Exact matches
            - ❌ No typo tolerance
            - ❌ Limited flexibility
            
            *Best for: Exact searches*
            """)
        
        with col2:
            st.markdown("""
            **🎯 pg_trgm Fuzzy**
            - ✅ Handles typos
            - ✅ Similarity scoring
            - ✅ Good performance
            - ❌ Still text-based
            
            *Best for: Flexible text search*
            """)
        
        with col3:
            st.markdown("""
            **🧠 pgvector Semantic**
            - ✅ Understands context
            - ✅ Conceptual matching
            - ✅ AI-powered insights
            - ❌ Requires setup
            
            *Best for: Intelligent search*
            """)

    else:
        st.info("💡 Configure PostgreSQL connection to try the search showcase.")
