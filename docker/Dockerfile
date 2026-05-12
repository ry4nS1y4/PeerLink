# =============================================================================
# Dockerfile - Python Application
# =============================================================================
# Customize for your tech stack.
# =============================================================================

# --- Build Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Production Stage ---
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "src.main"]

# =============================================================================
# Node.js Alternative (uncomment and remove Python above)
# =============================================================================
# FROM node:20-slim
# 
# WORKDIR /app
# 
# COPY package*.json ./
# RUN npm ci --only=production
# 
# COPY src/ ./src/
# 
# EXPOSE 3000
# 
# CMD ["node", "src/index.js"]

# =============================================================================
# Java/Spring Boot Alternative (uncomment and remove Python above)
# =============================================================================
# FROM eclipse-temurin:17-jdk-alpine as builder
# 
# WORKDIR /app
# COPY mvnw pom.xml ./
# COPY .mvn .mvn
# RUN ./mvnw dependency:go-offline
# 
# COPY src ./src
# RUN ./mvnw package -DskipTests
# 
# FROM eclipse-temurin:17-jre-alpine
# COPY --from=builder /app/target/*.jar app.jar
# EXPOSE 8080
# CMD ["java", "-jar", "app.jar"]
