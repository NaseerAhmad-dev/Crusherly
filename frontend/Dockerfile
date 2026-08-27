# Development image: runs the Angular CLI dev server with live reload against a bind-mounted
# source tree (see docker-compose.yml). Production builds/serving are handled by the CI "Build"
# stage (ng build) and a separate hosting target (Azure Static Web Apps / Container App +
# nginx) — not by this Dockerfile.
FROM node:22-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 4200

CMD ["npm", "start"]
