# CivilCode RAG

民法・判例（拡張予定）をRAGで検索し、自然言語の質問に対して**根拠条文付き**で回答する最小実装。

## 1) すぐ動かす

### A. Dockerで一撃
```bash
git clone <この内容をコピペするかzip展開>
cd civilcode-rag
docker compose up --build
# → http://localhost:3000 を開く（OpenAIキーなしでも動作。抽出要約モード）