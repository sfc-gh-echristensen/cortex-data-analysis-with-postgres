# 🧠 Semantic Search Setup with OpenAI Embeddings

This guide will help you set up real AI-powered semantic search using OpenAI embeddings and pgvector.

## 🎯 What You'll Get

- **Real semantic understanding**: Search for "morning drink" and find coffee transactions
- **Context-aware results**: Find conceptually similar transactions, not just text matches  
- **AI-powered insights**: Leverage OpenAI's embedding models for deep understanding
- **Similarity scoring**: See how closely results match your query

## 📋 Prerequisites

1. **PostgreSQL with pgvector extension**
2. **OpenAI API account and key**
3. **Python dependencies**

## 🚀 Step-by-Step Setup

### 1. Install pgvector Extension

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION vector;
```

### 2. Install Python Dependencies

```bash
pip install openai numpy pandas
```

Or install from requirements:

```bash
pip install -r requirements.txt
```

### 3. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

### 4. Set Environment Variable

**On macOS/Linux:**
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

**On Windows:**
```cmd
set OPENAI_API_KEY=sk-your-key-here
```

**Or add to your `.bashrc` or `.zshrc`:**
```bash
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 5. Run Embeddings Setup

```bash
python3 setup_embeddings.py
```

This script will:
- ✅ Add an `embedding` column to your transactions table
- ✅ Create vector similarity indexes
- ✅ Generate embeddings for all existing transactions
- ✅ Test semantic search functionality

## 🔍 Using Semantic Search

After setup, go to your Streamlit app:

1. Navigate to **"🔍 Search Demo"**
2. Select **"pgvector Semantic Search"**
3. Try these example queries:

### 🎯 Test Queries

**Conceptual Searches:**
- `"morning coffee drink"` → finds coffee shops, cafes
- `"subscription service"` → finds Netflix, Spotify, etc.
- `"grocery food shopping"` → finds supermarkets, markets
- `"ride transportation"` → finds Uber, Lyft, taxi

**Context Understanding:**
- `"fitness exercise"` → finds gyms, yoga studios
- `"streaming entertainment"` → finds video/music services
- `"fast food meal"` → finds quick service restaurants

## 📊 What to Expect

**With embeddings enabled, you'll see:**
- 🧠 **"Found X semantically similar transactions using AI embeddings!"**
- 📊 **Similarity scores** (0.600-1.000 range)
- 🚀 **"Real AI semantic search using OpenAI embeddings and pgvector!"**
- 📈 **Statistics** about your embedded transactions

## 🛠️ Troubleshooting

### No API Key Found
```
❌ OpenAI API key not found
```
**Solution:** Set the `OPENAI_API_KEY` environment variable

### Extension Missing
```
⚠️ pgvector extension not installed
```
**Solution:** Run `CREATE EXTENSION vector;` in PostgreSQL

### No Embeddings
```
⚠️ No embeddings found in database
```
**Solution:** Run `python3 setup_embeddings.py` to generate embeddings

### Import Error
```
❌ OpenAI library not installed
```
**Solution:** `pip install openai`

### Rate Limits
If you hit OpenAI rate limits, the setup script includes automatic retry delays.

## 💡 Cost Information

**OpenAI Embedding Costs (text-embedding-3-small):**
- **~$0.02 per 1M tokens**
- **Average transaction**: ~10-20 tokens
- **100 transactions**: ~$0.000002 (practically free)

**Performance:**
- **Initial setup**: One-time cost to embed existing data
- **Search queries**: ~$0.000002 per search
- **New transactions**: Auto-embedded when added

## 🔧 Advanced Configuration

### Custom Embedding Model

Edit `setup_embeddings.py` to use different models:

```python
config = EmbeddingConfig(
    model="text-embedding-3-large",  # Higher quality, more expensive
    dimensions=3072,                  # Larger dimensions
)
```

### Similarity Threshold

Adjust in the search query:

```sql
AND (1 - (embedding <=> :query_embedding::vector)) > 0.7  -- Higher = more strict
```

## ✅ Verification

After setup, you should see in your Streamlit app:

1. **pgvector Semantic Search** works without warnings
2. **Real AI similarity scores** in results
3. **Contextual matches** that ILIKE/pg_trgm miss
4. **"🚀 Real AI semantic search"** confirmation messages

## 🎉 Success!

Once set up, your search showcase will demonstrate:

1. **🔤 ILIKE**: Basic pattern matching
2. **🎯 pg_trgm**: Typo-tolerant fuzzy search  
3. **🧠 pgvector**: AI-powered semantic understanding

This creates a powerful demonstration of PostgreSQL's evolution from simple text search to advanced AI-powered semantic understanding!
