# 🤖 LLM Provider Configuration Guide

This guide helps you connect your preferred LLM and embedding providers to the New Tab backend service.

## 🚀 Quick Start

### Default Setup (OpenAI)

```bash
# 1. Get OpenAI API key from https://platform.openai.com/api-keys
# 2. Copy and configure environment
cp backend/.env.example backend/.env

# 3. Edit .env file:
API_TOKEN=sk-your-openai-api-key-here
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
```

### Other Providers

Choose your preferred combination:

| LLM Provider | Embedding Provider | Configuration |
|--------------|-------------------|---------------|
| **OpenAI** | **OpenAI** | Default, recommended |
| **Claude** | **OpenAI** | Fast LLM + reliable embeddings |
| **Groq** | **OpenAI** | Ultra-fast LLM + reliable embeddings |
| **ARK** | **ARK** | ByteDance internal |

## 📚 Provider Details

### 🔷 OpenAI (Recommended)

**Features:** Both LLM and embeddings, reliable, well-documented

```env
API_TOKEN=sk-your-openai-api-key-here
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-large
```

**Getting Started:**
1. Create account at [OpenAI Platform](https://platform.openai.com/)
2. Navigate to [API Keys](https://platform.openai.com/api-keys)
3. Create new secret key
4. Copy key to `API_TOKEN` in `.env`

**Models Available:**
- **LLM:** `gpt-4-turbo-preview`, `gpt-4`, `gpt-3.5-turbo`
- **Embedding:** `text-embedding-3-large` (3072d), `text-embedding-3-small` (1536d)

**Cost:** Pay-per-use, see [OpenAI Pricing](https://openai.com/pricing)

---

### 🧠 Claude (Anthropic)

**Features:** Advanced reasoning, safety-focused, no embeddings

```env
API_TOKEN=sk-ant-your-claude-api-key-here
LLM_PROVIDER=claude
EMBEDDING_PROVIDER=openai  # Claude doesn't provide embeddings
```

**Getting Started:**
1. Create account at [Anthropic Console](https://console.anthropic.com/)
2. Generate API key
3. For embeddings, also get OpenAI key (required)

**Models Available:**
- **LLM:** `claude-3-sonnet-20240229`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`

**Note:** You'll need **two API keys** - one for Claude (LLM) and one for OpenAI (embeddings)

---

### ⚡ Groq

**Features:** Ultra-fast inference, cost-effective, no embeddings

```env
API_TOKEN=gsk_your-groq-api-key-here
LLM_PROVIDER=groq
EMBEDDING_PROVIDER=openai  # Groq doesn't provide embeddings
LLM_MODEL=llama3-70b-8192
```

**Getting Started:**
1. Create account at [Groq Console](https://console.groq.com/)
2. Navigate to [API Keys](https://console.groq.com/keys)
3. Create new API key
4. For embeddings, also get OpenAI key (required)

**Models Available:**
- **LLM:** `llama3-70b-8192`, `llama3-8b-8192`, `mixtral-8x7b-32768`

**Performance:** Up to 500 tokens/second with LPU inference

---

### 🏢 ByteDance ARK

**Features:** Internal ByteDance platform, both LLM and embeddings

```env
API_TOKEN=your-ark-api-token-here
LLM_PROVIDER=ark
EMBEDDING_PROVIDER=ark
LLM_ENDPOINT=https://ark-cn-beijing.bytedance.net/api/v3/chat/completions
EMBEDDING_ENDPOINT=https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal
LLM_MODEL=ep-20250529215531-dfpgt
EMBEDDING_MODEL=ep-20250529220411-grkkv
```

**Getting Started:**
1. Get access to ByteDance ARK platform
2. Obtain API token from ARK dashboard
3. Use provided endpoint URLs and model IDs

## 🔧 Advanced Configuration

### Mixed Provider Setup

Use different providers for LLM and embeddings:

```env
# Example: Claude for reasoning + OpenAI for embeddings
API_TOKEN=sk-ant-your-claude-key  # Primary provider key
LLM_PROVIDER=claude
EMBEDDING_PROVIDER=openai
```

**Note:** When using different providers, you typically need separate API keys. Set the primary key in `API_TOKEN`.

### Custom Endpoints

Override default provider URLs:

```env
# Custom OpenAI-compatible endpoint
LLM_PROVIDER=openai
LLM_ENDPOINT=https://your-custom-endpoint.com/v1/chat/completions
EMBEDDING_ENDPOINT=https://your-custom-endpoint.com/v1/embeddings
```

### Model Selection

Override default models:

```env
# Use different OpenAI models
LLM_MODEL=gpt-3.5-turbo      # Faster, cheaper
EMBEDDING_MODEL=text-embedding-3-small  # Smaller, faster
```

## 🎯 Use Case Recommendations

### 🏃‍♂️ Speed-Focused
```env
LLM_PROVIDER=groq
LLM_MODEL=llama3-8b-8192
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

### 💰 Cost-Optimized
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

### 🎯 Quality-Focused
```env
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
```

### 🔒 Privacy-Focused (On-Premise)
```env
# Use local OpenAI-compatible server
LLM_PROVIDER=openai
LLM_ENDPOINT=http://localhost:8080/v1/chat/completions
EMBEDDING_ENDPOINT=http://localhost:8080/v1/embeddings
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Error: API_TOKEN cannot be empty
```
**Solution:** Ensure `API_TOKEN` is set in your `.env` file

#### 2. Provider Compatibility
```
Error: Provider 'claude' does not support embeddings
```
**Solution:** Use `openai` or `ark` for embeddings:
```env
EMBEDDING_PROVIDER=openai
```

#### 3. Model Not Found
```
Error: Model 'invalid-model' not found
```
**Solution:** Check provider documentation for valid model names

#### 4. Rate Limiting
```
Error: Rate limit exceeded
```
**Solution:** The system automatically retries with exponential backoff. Consider upgrading your API plan.

### Health Check

Test your configuration:

```bash
# Check if providers are working
curl http://localhost:8000/health

# Example response:
{
  "status": "healthy",
  "llm_provider": {
    "provider_type": "OpenAIProvider",
    "status": "healthy",
    "response_time_ms": 245,
    "model": "gpt-4-turbo-preview"
  },
  "embedding_provider": {
    "provider_type": "OpenAIProvider", 
    "status": "available",
    "dimension": 3072
  }
}
```

### Debug Mode

Enable detailed logging:

```env
LOG_LEVEL=debug
```

## 📊 Performance Comparison

| Provider | Speed | Cost | Quality | Embedding Support |
|----------|-------|------|---------|-------------------|
| **OpenAI** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| **Claude** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| **Groq** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| **ARK** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ |

## 🔄 Migration Guide

### From ARK to OpenAI

1. **Backup your current `.env`:**
   ```bash
   cp backend/.env backend/.env.ark.backup
   ```

2. **Update configuration:**
   ```env
   # Old ARK setup
   ARK_API_TOKEN=your-ark-token
   
   # New OpenAI setup
   API_TOKEN=sk-your-openai-key
   LLM_PROVIDER=openai
   EMBEDDING_PROVIDER=openai
   ```

3. **Test the change:**
   ```bash
   docker compose restart backend
   curl http://localhost:8000/health
   ```

### Rollback Plan

Keep your ARK configuration in `.env.ark`:

```bash
# Quick rollback
cp backend/.env.ark backend/.env
docker compose restart backend
```

## 🔐 Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for production
3. **Rotate keys regularly** 
4. **Monitor usage** through provider dashboards
5. **Set up billing alerts** to avoid unexpected charges

## 🆘 Getting Help

- **Configuration Issues:** Check this guide first
- **Provider-specific:** Consult provider documentation
- **New Provider Requests:** Open an issue in the repository
- **Performance Issues:** Enable debug logging and share logs

## 📖 Adding New Providers

Want to add a new provider? See our [Developer Guide](./DEVELOPER_GUIDE.md) for implementing custom providers.

---

**Quick Links:**
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Claude API Docs](https://docs.anthropic.com/)
- [Groq API Docs](https://console.groq.com/docs)
- [Configuration Reference](./backend/.env.example)