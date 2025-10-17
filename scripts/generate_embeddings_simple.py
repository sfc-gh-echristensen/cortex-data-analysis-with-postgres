#!/usr/bin/env python3
"""
Simple script to generate embeddings using raw psycopg2 to avoid SQLAlchemy parameter issues.
"""
import os
import psycopg2
import openai
from typing import List

def get_postgres_config():
    """Get PostgreSQL connection parameters from secrets.toml"""
    import toml
    
    secrets_path = ".streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        raise FileNotFoundError(f"Secrets file not found at {secrets_path}")
    
    config = toml.load(secrets_path)
    return config['postgres']

def generate_embedding(client, text: str) -> List[float]:
    """Generate embedding for text using OpenAI."""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text.strip()
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None

def main():
    print("🚀 Simple Embeddings Generator")
    print("=" * 50)
    
    # Check OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not found")
        return
    
    client = openai.OpenAI(api_key=api_key)
    print("✅ OpenAI client initialized")
    
    # Get database connection
    config = get_postgres_config()
    conn = psycopg2.connect(
        host=config['host'],
        database=config['database'], 
        user=config['user'],
        password=config['password'],
        port=config.get('port', 5432)
    )
    conn.autocommit = True
    print("✅ Database connected")
    
    # Get transactions without embeddings
    cursor = conn.cursor()
    cursor.execute("""
        SELECT transaction_id, merchant, notes 
        FROM transactions 
        WHERE embedding IS NULL 
        ORDER BY transaction_id 
        LIMIT 10
    """)
    
    transactions = cursor.fetchall()
    print(f"📊 Found {len(transactions)} transactions without embeddings")
    
    if not transactions:
        print("✅ All transactions already have embeddings!")
        return
    
    # Generate embeddings for first few transactions
    for i, (transaction_id, merchant, notes) in enumerate(transactions):
        search_text = f"{merchant} {notes or ''}".strip()
        print(f"\n🔄 Processing transaction {transaction_id}: '{search_text[:50]}...'")
        
        # Generate embedding
        embedding = generate_embedding(client, search_text)
        
        if embedding:
            # Store embedding using raw SQL
            embedding_str = str(embedding)
            cursor.execute("""
                UPDATE transactions 
                SET embedding = %s::vector
                WHERE transaction_id = %s
            """, (embedding_str, transaction_id))
            
            print(f"  ✅ Successfully stored embedding for transaction {transaction_id}")
        else:
            print(f"  ❌ Failed to generate embedding for transaction {transaction_id}")
    
    # Test the embeddings
    print(f"\n🔍 Testing semantic search...")
    test_query = "coffee shop"
    query_embedding = generate_embedding(client, test_query)
    
    if query_embedding:
        cursor.execute("""
            SELECT 
                transaction_id,
                merchant,
                notes,
                (1 - (embedding <=> %s::vector)) as similarity
            FROM transactions 
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT 3
        """, (str(query_embedding), str(query_embedding)))
        
        results = cursor.fetchall()
        print(f"🔎 Query: '{test_query}' - Found {len(results)} similar transactions:")
        for tx_id, merchant, notes, similarity in results:
            print(f"  • Transaction {tx_id}: {merchant} - {similarity:.3f} similarity")
    
    cursor.close()
    conn.close()
    print(f"\n✅ Complete!")

if __name__ == "__main__":
    main()
