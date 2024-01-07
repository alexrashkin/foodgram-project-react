FROM node:13.12.0-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm cache clean --force
RUN npm install --legacy-peer-deps
COPY . ./
RUN npm install --legacy-peer-deps
RUN npm install react-meta-tags --legacy-peer-deps
RUN npm run build
RUN npm install -g http-server
CMD ["http-server", "-p", "8002", "./build"]