#!/usr/bin/env python3
"""
Set up pgvector embeddings for semantic search.

This script:
1. Adds an embeddings column to the transactions table
2. Sets up OpenAI API integration for generating embeddings
3. Generates embeddings for existing transactions
4. Provides utilities for semantic search
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from db_utils import get_db_connection, create_postgres_engine
from sqlalchemy import text
import pandas as pd

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️  OpenAI library not installed. Install with: pip install openai")

@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model: str = "text-embedding-3-small"  # Cheaper and faster than ada-002
    dimensions: int = 1536  # Standard dimension for text-embedding-3-small
    chunk_size: int = 100   # Process transactions in chunks
    api_key: Optional[str] = None

class EmbeddingManager:
    """Manage embeddings for transaction search."""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client = None
        
        if HAS_OPENAI:
            # Try to get API key from multiple sources
            api_key = (
                config.api_key or
                os.getenv('OPENAI_API_KEY') or
                os.getenv('OPENAI_KEY')
            )
            
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
                print(f"✅ OpenAI client initialized with model: {config.model}")
            else:
                print("❌ OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
    def setup_database(self) -> bool:
        """Add embeddings column to transactions table."""
        try:
            with get_db_connection() as conn:
                # Check if pgvector extension exists
                result = conn.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension WHERE extname = 'vector'
                    ) as has_vector
                """)).fetchone()
                
                if not result.has_vector:
                    print("❌ pgvector extension not found!")
                    print("Install with: CREATE EXTENSION vector;")
                    return False
                
                # Check if embeddings column exists
                result = conn.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'transactions' 
                        AND column_name = 'embedding'
                    ) as has_embedding
                """)).fetchone()
                
                if not result.has_embedding:
                    print(f"📊 Adding embeddings column (vector({self.config.dimensions}))...")
                    conn.execute(text(f"""
                        ALTER TABLE transactions 
                        ADD COLUMN embedding vector({self.config.dimensions})
                    """))
                    conn.commit()
                    print("✅ Embeddings column added!")
                else:
                    print("✅ Embeddings column already exists")
            
            # Create index separately with autocommit
            self._create_vector_index()
            return True
                
        except Exception as e:
            print(f"❌ Database setup error: {e}")
            return False
    
    def _create_vector_index(self) -> bool:
        """Create vector similarity index using autocommit."""
        try:
            # Create a new connection with autocommit for index creation
            engine = create_postgres_engine()
            with engine.connect() as conn:
                # Set autocommit mode
                conn.connection.set_session(autocommit=True)
                
                # Check if index exists
                result = conn.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = 'idx_transactions_embedding_cosine'
                    ) as has_index
                """)).fetchone()
                
                if not result.has_index:
                    print("🔍 Creating vector similarity index...")
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY idx_transactions_embedding_cosine 
                        ON transactions USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100)
                    """))
                    print("✅ Vector index created successfully!")
                else:
                    print("✅ Vector index already exists!")
                    
            return True
            
        except Exception as e:
            print(f"⚠️  Index creation warning: {e}")
            print("   You can create the index manually later for better performance:")
            print("   CREATE INDEX CONCURRENTLY idx_transactions_embedding_cosine ON transactions USING ivfflat (embedding vector_cosine_ops);")
            return True  # Don't fail the whole setup for index issues
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not self.client:
            return None
            
        try:
            response = self.client.embeddings.create(
                model=self.config.model,
                input=text.strip()
            )
            return response.data[0].embedding
            
        except Exception as e:
            print(f"❌ Embedding generation error: {e}")
            return None
    
    def create_searchable_text(self, merchant: str, notes: str, category: str) -> str:
        """Create combined text for embedding generation."""
        # Combine merchant, notes, and category for richer semantic content
        parts = []
        
        if merchant and merchant.strip():
            parts.append(merchant.strip())
        
        if notes and notes.strip() and not notes.startswith('Search demo'):
            parts.append(notes.strip())
        
        if category and category.strip():
            parts.append(f"Category: {category.strip()}")
        
        return " | ".join(parts) if parts else merchant or "transaction"
    
    def generate_embeddings_for_existing_data(self) -> bool:
        """Generate embeddings for all transactions without embeddings."""
        if not self.client:
            print("❌ OpenAI client not available")
            return False
        
        try:
            with get_db_connection() as conn:
                # Get transactions without embeddings
                result = conn.execute(text("""
                    SELECT 
                        transaction_id,
                        merchant,
                        COALESCE(notes, '') as notes,
                        COALESCE(category, '') as category
                    FROM transactions 
                    WHERE embedding IS NULL
                    ORDER BY transaction_id
                """)).fetchall()
                
                if not result:
                    print("✅ All transactions already have embeddings")
                    return True
                
                transactions = [dict(row._mapping) for row in result]
                print(f"📊 Found {len(transactions)} transactions without embeddings")
                
                # Process in chunks to avoid API rate limits
                total_processed = 0
                total_errors = 0
                
                for i in range(0, len(transactions), self.config.chunk_size):
                    chunk = transactions[i:i + self.config.chunk_size]
                    print(f"🔄 Processing chunk {i//self.config.chunk_size + 1}/{(len(transactions)-1)//self.config.chunk_size + 1} ({len(chunk)} transactions)...")
                    
                    for txn in chunk:
                        try:
                            # Create searchable text
                            search_text = self.create_searchable_text(
                                txn['merchant'], 
                                txn['notes'], 
                                txn['category']
                            )
                            
                            # Generate embedding
                            embedding = self.generate_embedding(search_text)
                            
                            if embedding:
                                # Store embedding in database
                                conn.execute(text("""
                                    UPDATE transactions 
                                    SET embedding = %(embedding)s::vector
                                    WHERE transaction_id = %(transaction_id)s
                                """), {
                                    'embedding': str(embedding),
                                    'transaction_id': txn['transaction_id']
                                })
                                
                                total_processed += 1
                                
                                if total_processed % 10 == 0:
                                    print(f"  ✅ Processed {total_processed} embeddings...")
                            else:
                                total_errors += 1
                                print(f"  ❌ Failed to generate embedding for transaction {txn['transaction_id']}")
                                
                        except Exception as e:
                            total_errors += 1
                            print(f"  ❌ Error processing transaction {txn['transaction_id']}: {e}")
                    
                    # Commit after each chunk
                    conn.commit()
                    
                    # Small delay to be nice to the API
                    import time
                    time.sleep(0.1)
                
                print(f"🎉 Embedding generation complete!")
                print(f"  ✅ Successfully processed: {total_processed}")
                print(f"  ❌ Errors: {total_errors}")
                
                return total_errors == 0
                
        except Exception as e:
            print(f"❌ Embedding generation error: {e}")
            return False
    
    def search_similar_transactions(self, query: str, limit: int = 20, similarity_threshold: float = 0.7) -> List[Dict]:
        """Search for semantically similar transactions."""
        if not self.client:
            print("❌ OpenAI client not available")
            return []
        
        try:
            # Generate embedding for search query
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                return []
            
            with get_db_connection() as conn:
                # Use cosine similarity search
                result = conn.execute(text("""
                    SELECT 
                        transaction_id,
                        merchant,
                        notes,
                        amount,
                        date,
                        category,
                        (1 - (embedding <=> %(query_embedding)s::vector)) as similarity
                    FROM transactions 
                    WHERE embedding IS NOT NULL
                      AND status = 'approved'
                      AND (1 - (embedding <=> %(query_embedding)s::vector)) > %(threshold)s
                    ORDER BY embedding <=> %(query_embedding)s::vector
                    LIMIT %(limit)s
                """), {
                    'query_embedding': str(query_embedding),
                    'threshold': similarity_threshold,
                    'limit': limit
                }).fetchall()
                
                return [dict(row._mapping) for row in result]
                
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []
    
    def get_embedding_stats(self) -> Dict:
        """Get statistics about embeddings in the database."""
        try:
            with get_db_connection() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(embedding) as transactions_with_embeddings,
                        COUNT(*) - COUNT(embedding) as transactions_without_embeddings
                    FROM transactions
                """)).fetchone()
                
                return dict(result._mapping) if result else {}
                
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return {}

def main():
    """Main setup and testing function."""
    print("🚀 PostgreSQL Embeddings Setup")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OpenAI API key required!")
        print("Set your API key: export OPENAI_API_KEY='your-key-here'")
        print("Get your key from: https://platform.openai.com/api-keys")
        return False
    
    # Initialize embedding manager
    config = EmbeddingConfig()
    manager = EmbeddingManager(config)
    
    # Setup database
    print("\n🔧 Setting up database schema...")
    if not manager.setup_database():
        return False
    
    # Generate embeddings for existing data
    print("\n📊 Generating embeddings for existing transactions...")
    if not manager.generate_embeddings_for_existing_data():
        print("⚠️  Some embeddings failed to generate, but continuing...")
    
    # Show stats
    print("\n📈 Embedding Statistics:")
    stats = manager.get_embedding_stats()
    if stats:
        print(f"  Total transactions: {stats.get('total_transactions', 0)}")
        print(f"  With embeddings: {stats.get('transactions_with_embeddings', 0)}")
        print(f"  Without embeddings: {stats.get('transactions_without_embeddings', 0)}")
    
    # Test semantic search
    print("\n🔍 Testing semantic search...")
    test_queries = [
        "morning coffee drink",
        "subscription service",
        "grocery food shopping",
        "ride transportation"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Query: '{query}'")
        results = manager.search_similar_transactions(query, limit=3)
        if results:
            for result in results:
                print(f"  • {result['merchant']} (${result['amount']:.2f}) - Similarity: {result['similarity']:.3f}")
        else:
            print("  No results found")
    
    print("\n✅ Embeddings setup complete!")
    print("🚀 Your semantic search is now ready to use in the Streamlit app!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
