# Frontend: qurish va nginx bilan tarqatish.
#
# Ikki bosqichli — bu yerda oqlanadi: Node va npm paketlari (300+ MB)
# yakuniy tasvirga tushmaydi, faqat qurilgan statik fayllar qoladi.

FROM node:24-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build-only

# --- Tarqatish ---

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
