# Docker Setup for LiveKit Call Center

This guide explains how to run the LiveKit Call Center application using Docker and Docker Compose.

## 🐳 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Development Setup

1. **Clone and navigate to the repository**
   ```bash
   git clone <your-repo-url>
   cd livekit-callcenter
   ```

2. **Create environment file**
   ```bash
   cp docker.env.example .env
   # Edit .env with your LiveKit configuration
   ```

3. **Run with development configuration**
   ```bash
   # Build and start the development environment
   docker-compose -f docker-compose.dev.yml up --build

   # Or run in background
   docker-compose -f docker-compose.dev.yml up -d --build
   ```

4. **Access the application**
   - Web interface: http://localhost:8000
   - API docs: http://localhost:8000/docs

### Production Setup

1. **Configure environment variables**
   ```bash
   cp docker.env.example .env
   # Update .env with production values:
   # - Strong SECRET_KEY
   # - PostgreSQL database settings
   # - LiveKit production credentials
   ```

2. **Run production stack**
   ```bash
   # Start all services (web app + PostgreSQL + Redis)
   docker-compose up -d --build

   # View logs
   docker-compose logs -f web
   ```

3. **Initialize database**
   ```bash
   # Run database migrations
   docker-compose exec web python -c "from app.database.db import engine, Base; Base.metadata.create_all(bind=engine)"

   # Create first agent (optional)
   docker-compose exec web python scripts/register_agent.py
   ```

## 📋 Available Services

### Core Services

- **web**: FastAPI application (port 8000)
- **db**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)

### Optional Services

- **livekit**: Local LiveKit server (ports 7880-7882)

## 🛠️ Docker Commands

### Basic Operations

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Execute commands in container
docker-compose exec web bash
docker-compose exec web python scripts/register_agent.py
```

### Database Operations

```bash
# Initialize database
docker-compose exec web python -c "from app.database.db import engine, Base; Base.metadata.create_all(bind=engine)"

# Access PostgreSQL
docker-compose exec db psql -U callcenter_user -d callcenter

# Backup database
docker-compose exec db pg_dump -U callcenter_user callcenter > backup.sql

# Restore database
docker-compose exec -T db psql -U callcenter_user callcenter < backup.sql
```

### Development Commands

```bash
# Run with hot reload (development)
docker-compose -f docker-compose.dev.yml up --build

# Run tests
docker-compose exec web python -m pytest

# Install new dependencies
docker-compose exec web pip install package_name
docker-compose exec web pip freeze > requirements.txt
```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `docker.env.example`):

```env
# Required LiveKit settings
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
LIVEKIT_URL=https://your-livekit-server.com
LIVEKIT_WS_URL=wss://your-livekit-server.com

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://callcenter_user:password@db:5432/callcenter

# Security
SECRET_KEY=your-strong-secret-key
```

### Volume Mounts

- `./data`: SQLite database files (development)
- `./logs`: Application logs
- `postgres_data`: PostgreSQL data (production)
- `redis_data`: Redis data

### Networking

All services communicate through the `callcenter-network` bridge network.

## 🔍 Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Change ports in docker-compose.yml if needed
   ports:
     - "8001:8000"  # Change external port
   ```

2. **Database connection issues**
   ```bash
   # Check database logs
   docker-compose logs db
   
   # Verify database is running
   docker-compose ps
   ```

3. **LiveKit connection problems**
   ```bash
   # Check environment variables
   docker-compose exec web env | grep LIVEKIT
   
   # Verify network connectivity
   docker-compose exec web ping your-livekit-server.com
   ```

4. **Permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER ./data ./logs
   chmod 755 ./data ./logs
   ```

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check all services status
docker-compose ps

# View resource usage
docker-compose top
```

### Cleanup

```bash
# Remove containers and networks
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove containers, networks, volumes, and images
docker-compose down -v --rmi all

# Clean up Docker system
docker system prune -a
```

## 🚀 Deployment

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml callcenter

# Scale services
docker service scale callcenter_web=3
```

### Using Kubernetes

Convert Docker Compose to Kubernetes manifests:

```bash
# Install kompose
curl -L https://github.com/kubernetes/kompose/releases/latest/download/kompose-linux-amd64 -o kompose
chmod +x kompose
sudo mv kompose /usr/local/bin

# Convert to Kubernetes
kompose convert

# Apply to cluster
kubectl apply -f .
```

## 📝 Best Practices

1. **Security**
   - Use strong, unique SECRET_KEY in production
   - Don't commit .env files to version control
   - Regularly update base images
   - Use non-root user in containers (already configured)

2. **Performance**
   - Use multi-stage builds for smaller images
   - Implement proper health checks
   - Monitor resource usage
   - Use Redis for caching in production

3. **Monitoring**
   - Collect logs centrally
   - Monitor database performance
   - Set up alerts for service failures
   - Track application metrics

4. **Backup**
   - Regular database backups
   - Backup volume data
   - Test restore procedures
   - Store backups securely 