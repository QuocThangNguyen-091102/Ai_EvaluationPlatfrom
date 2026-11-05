FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# MVP chạy bằng dev server của Vite (đủ cho demo cục bộ).
CMD ["npm", "run", "dev"]
