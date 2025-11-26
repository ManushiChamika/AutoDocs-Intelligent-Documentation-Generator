FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps || npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
