FROM node:20-bookworm-slim AS builder

WORKDIR /app

ARG NEXT_PUBLIC_HG_API_BASE=http://localhost:8080
ARG NEXT_PUBLIC_HG_SSE_URL=
ARG NEXT_PUBLIC_HG_WS_URL=
ARG NEXT_PUBLIC_DEMO_OPERATOR_KEY=
ENV NEXT_PUBLIC_HG_API_BASE=$NEXT_PUBLIC_HG_API_BASE
ENV NEXT_PUBLIC_HG_SSE_URL=$NEXT_PUBLIC_HG_SSE_URL
ENV NEXT_PUBLIC_HG_WS_URL=$NEXT_PUBLIC_HG_WS_URL
ENV NEXT_PUBLIC_DEMO_OPERATOR_KEY=$NEXT_PUBLIC_DEMO_OPERATOR_KEY

COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3001

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3001
CMD ["node", "server.js"]
