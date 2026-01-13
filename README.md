# Flash Sale Concurrency Engine 🔥

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20ALB%20%7C%20ElastiCache-FF9900?style=flat&logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/)
[![Docker](https://img.shields.io/badge/Docker-Production%20Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

A **production-grade** inventory management system architected for **AWS**, demonstrating **race condition** prevention in high-concurrency e-commerce scenarios. Implements atomic stock control using **Redis Lua Scripts** with horizontal scalability via **Auto Scaling Groups**.

> ⚠️ **Cost Optimization Notice:** The live AWS infrastructure (EC2 instances, ALB, ElastiCache) is currently **spun down** to minimize costs. This repository contains all configuration necessary for deployment. See [Deployment Guide](#-deployment) for instructions.

---

## 🏗️ Production Architecture

The system is designed for **horizontal scalability** on AWS, leveraging managed services for high availability.

```
                                    ┌─────────────────────────────────────┐
                                    │           ROUTE 53                  │
                                    │      (DNS / Domain Routing)         │
                                    └─────────────────┬───────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AWS VPC (10.0.0.0/16)                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                     APPLICATION LOAD BALANCER (ALB)                           │  │
│  │                   • Health checks on /health endpoint                         │  │
│  │                   • SSL/TLS termination                                       │  │
│  │                   • Path-based routing                                        │  │
│  └───────────────────────────────────┬───────────────────────────────────────────┘  │
│                                      │                                              │
│           ┌──────────────────────────┼──────────────────────────┐                   │
│           ▼                          ▼                          ▼                   │
│  ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐         │
│  │   EC2 (t3.medium)│        │   EC2 (t3.medium)│        │   EC2 (t3.medium)│         │
│  │   ┌───────────┐ │        │   ┌───────────┐ │        │   ┌───────────┐ │         │
│  │   │  Docker   │ │        │   │  Docker   │ │        │   │  Docker   │ │         │
│  │   │ Container │ │        │   │ Container │ │        │   │ Container │ │         │
│  │   │ (FastAPI) │ │        │   │ (FastAPI) │ │        │   │ (FastAPI) │ │         │
│  │   └───────────┘ │        │   └───────────┘ │        │   └───────────┘ │         │
│  │  Public Subnet  │        │  Public Subnet  │        │  Public Subnet  │         │
│  │    (AZ-1a)      │        │    (AZ-1b)      │        │    (AZ-1c)      │         │
│  └────────┬────────┘        └────────┬────────┘        └────────┬────────┘         │
│           │                          │                          │                   │
│           └──────────────────────────┼──────────────────────────┘                   │
│                      AUTO SCALING GROUP (min: 2, max: 10)                           │
│                                      │                                              │
│                                      ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                        AMAZON ELASTICACHE (Redis 7)                           │  │
│  │                   • Cluster mode enabled                                      │  │
│  │                   • Multi-AZ replication                                      │  │
│  │                   • Atomic Lua Script execution                               │  │
│  │                              Private Subnet                                   │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Infrastructure Components

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| **Compute** | EC2 + Auto Scaling | Horizontal scaling based on CPU/request metrics |
| **Load Balancing** | Application Load Balancer | Traffic distribution, health checks, SSL termination |
| **Caching/Locking** | ElastiCache (Redis) | Distributed locking, atomic operations, session management |
| **Networking** | VPC + Subnets | Network isolation, security groups, private connectivity |

---

## � The Problem: Race Conditions in Flash Sales

When thousands of users attempt to purchase limited inventory simultaneously, traditional **Read-Modify-Write** patterns fail catastrophically.

### Performance Results

![Attack Results](./assets/images/attack_results.png)

| Metric | Unsafe Method | Safe Method | Analysis |
| :--- | :--- | :--- | :--- |
| **Successful Sales** | 500 ❌ | 50 ✅ | Unsafe allowed 450 phantom sales |
| **Final Stock** | 43 (should be 0) | 0 (perfect) | Race condition corrupted state |
| **Execution Time** | ~0.44s | ~0.14s | Lua scripts reduce round-trips |
| **Data Integrity** | **BROKEN** | **GUARANTEED** | Atomic operations prevent overselling |

> **Business Impact:** The unsafe method sold 500 items when only 50 existed. In production, this means 450 customers receive refunds, support tickets spike, and brand reputation suffers.

---

## 🛠️ Technical Implementation

### The Race Condition (Vulnerable Pattern)
```python
async def purchase_item_unsafe(self) -> bool:
    stock = await self.redis.get(self.STOCK_KEY)     # READ
    if int(stock) > 0:
        # ⚠️ RACE CONDITION WINDOW - Another request reads same value
        await self.redis.set(self.STOCK_KEY, stock - 1)  # WRITE
        return True
    return False
```

### The Solution: Atomic Lua Scripts
```python
async def purchase_item_safe(self) -> bool:
    lua_script = """
    local stock = redis.call('GET', KEYS[1])
    if stock and tonumber(stock) > 0 then
        redis.call('DECR', KEYS[1])
        return 1
    end
    return 0
    """
    result = await self.redis.eval(lua_script, 1, self.STOCK_KEY)
    return bool(result)
```

### Why Lua Scripts Work
- **Redis is Single-Threaded:** Commands execute sequentially, no interleaving
- **Script Atomicity:** Entire script runs as one transaction
- **Network Efficiency:** Logic executes server-side, reducing latency

---

## � Deployment

### Local Development
```bash
# Clone the repository
git clone https://github.com/Nehuen1304/flash-sale-concurrency-engine.git
cd flash-sale-concurrency-engine

# Start services
docker-compose up -d --build

# Verify health
curl http://localhost:8000/health

# Run attack simulation
pip install aiohttp
python scripts/attack.py
```

### AWS Production Deployment

1. **Build and Push Docker Image**
```bash
# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Build production image
docker build -t flash-sale-engine:latest .

# Tag and push
docker tag flash-sale-engine:latest <account>.dkr.ecr.us-east-1.amazonaws.com/flash-sale-engine:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/flash-sale-engine:latest
```

2. **Configure ElastiCache Connection**
```bash
# Set environment variables on EC2 instances
export REDIS_HOST=flash-sale-cluster.xxxxx.cache.amazonaws.com
export REDIS_PORT=6379
```

3. **Deploy to EC2 with User Data**
```bash
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
docker pull <account>.dkr.ecr.us-east-1.amazonaws.com/flash-sale-engine:latest
docker run -d -p 8000:8000 \
  -e REDIS_HOST=${REDIS_HOST} \
  -e REDIS_PORT=6379 \
  flash-sale-engine:latest
```

---

## 📂 Project Structure

```bash
├── app/
│   ├── main.py              # FastAPI application with health endpoints
│   ├── database.py          # Redis Singleton with connection pooling
│   └── inventory_service.py # Atomic vs non-atomic purchase logic
├── scripts/
│   └── attack.py            # Concurrent load simulation (aiohttp)
├── assets/
│   └── images/              # Documentation assets
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Local development & testing
└── requirements.txt         # Python dependencies
```

---

## 🧠 Engineering Concepts Demonstrated

| Concept | Implementation |
|---------|----------------|
| **Race Conditions** | Non-atomic Read-Modify-Write vulnerability |
| **Distributed Locking** | Redis Lua Scripts for atomicity |
| **Horizontal Scaling** | Stateless containers behind ALB |
| **Connection Pooling** | Singleton pattern with `max_connections` |
| **Health Checks** | `/health` endpoint for ALB target groups |
| **Infrastructure as Code** | Docker + Compose for reproducible deployments |

---

## 📚 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Application** | FastAPI + Python 3.11 | Async web framework |
| **Data Store** | Redis 7 / ElastiCache | Atomic operations, distributed locking |
| **Compute** | EC2 + Auto Scaling | Horizontal scalability |
| **Networking** | ALB + VPC | Load balancing, network isolation |
| **Container** | Docker | Consistent deployment artifact |

---

## 📝 Author

Developed as a **Backend Architecture** showcase demonstrating distributed systems, cloud infrastructure, and high-concurrency patterns.
