FROM node:20-alpine
RUN corepack enable

WORKDIR /app
# 依存解決前に主要ファイルをコピー
COPY package.json next.config.js tsconfig.json ./
# アプリ本体
COPY app ./app
COPY components ./components

# lockfile が無くても動くように（ある場合は尊重）
RUN pnpm install --frozen-lockfile || pnpm install
RUN pnpm build

EXPOSE 3000
CMD ["pnpm", "start"]