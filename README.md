# 🌌 Galaxy of Knowledge

> An interactive 3D universe of NASA research papers powered by AI and advanced visualization

[![System Architecture](Gok.drawio.png)](Gok.drawio.png)

## 🚀 Overview

Galaxy of Knowledge is an innovative research discovery platform that transforms the way scientists and researchers explore NASA's vast repository of biological and space science publications. Using cutting-edge AI, vector embeddings, and immersive 3D visualization, the platform creates an interactive "universe" where each research paper becomes a celestial body in a knowledge galaxy.

### 🎯 Key Features

- **🌟 3D Interactive Universe**: Navigate through research papers visualized as stars and planets in a 3D space
- **🤖 AI-Powered Analysis**: Advanced paper analysis using Google's Gemini AI and vector embeddings
- **📊 Semantic Search**: Find related papers through intelligent semantic similarity
- **💬 Research Chatbot**: Interactive AI agent for deep exploration and hypothesis generation
- **🔍 Knowledge Graph**: Discover hidden connections between research topics
- **📈 Real-time Analytics**: Track research trends and citation networks

## 🖼️ Application Screenshots

### Main Universe View
![Galaxy Universe Interface](read%20paper.jpg)

The main interface presents research papers as celestial bodies in an interactive 3D space. Users can "fly through" the galaxy of knowledge, with paper clustering based on semantic similarity creating natural research neighborhoods.

### System Architecture
![System Architecture Diagram](Gok.drawio.png)

Our architecture follows a 7-step process:
1. **Data Ingestion**: Crawl NASA biology publications using Crawl4AI
2. **Content Processing**: Convert to Markdown and JSON format
3. **AI Processing**: Extract knowledge using advanced NLP
4. **Vector Storage**: Store semantic embeddings in vector database
5. **3D Visualization**: Interactive universe interface
6. **AI Agent**: Deep exploration with knowledge graph support
7. **Hypothesis Generation**: Research investment and hypothesis agent

## 🏗️ Architecture

### Backend Components

- **FastAPI Application**: High-performance async API serving research data
- **Vector Database**: PostgreSQL with pgvector for semantic search
- **AI Services**: Google Vertex AI integration with Gemini models
- **Knowledge Graph**: LightRAG-powered relationship extraction
- **MCP Server**: Model Context Protocol for advanced AI interactions

### Frontend Technology Stack

- **React 18** with **TypeScript** for robust component development
- **Three.js** via **@react-three/fiber** for 3D universe visualization
- **Vite** for lightning-fast development and building
- **Tailwind CSS** for modern, responsive design
- **Radix UI** components for accessible interface elements

### Data Pipeline

- **Crawl4AI**: Intelligent web scraping of research publications
- **Async Processing**: High-performance concurrent data processing
- **Content Extraction**: Advanced parsing from Abstract to References
- **Structured Storage**: JSON-based research paper storage

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (3.10 or 3.11 recommended)
- **Node.js 18+** and **npm**
- **PostgreSQL 14+** with pgvector extension
- **Google Cloud Project** with Vertex AI API enabled

### Backend Setup

1. **Clone and setup environment**:
   ```powershell
   git clone https://github.com/your-username/Galaxy-of-Knowledge.git
   cd Galaxy-of-Knowledge/backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. **Install Python dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure Google Cloud credentials**:
   ```powershell
   # Place your service_account.json in the backend folder
   $env:GOOGLE_APPLICATION_CREDENTIALS = "service_account.json"
   ```

4. **Setup PostgreSQL database**:
   ```powershell
   # Create database and enable pgvector extension
   # Update database connection settings in database/connect.py
   ```

5. **Start the backend server**:
   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**:
   ```powershell
   cd ../frontend
   ```

2. **Install dependencies**:
   ```powershell
   npm install
   ```

3. **Start development server**:
   ```powershell
   npm run dev
   ```

4. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Data Pipeline Setup

1. **Setup data crawler**:
   ```powershell
   cd ../data_pipeline
   pip install -r requirements.txt
   playwright install
   ```

2. **Run the crawler**:
   ```powershell
   python crawl_data.py
   ```

## 📊 API Endpoints

### Core Research APIs
- `GET /api/v1/papers/` - Retrieve research papers
- `GET /api/v1/search/` - Semantic search functionality  
- `GET /api/v1/clusters/` - Paper clustering data
- `POST /api/v1/paper-analysis/` - AI-powered paper analysis

### Analytics & Visualization
- `GET /api/v1/stats/` - Research statistics and metrics
- `GET /api/v1/graph/` - Knowledge graph relationships

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/galaxy_knowledge
PGVECTOR_CONNECTION_STRING=postgresql://username:password@localhost:5432/galaxy_knowledge

# Google Cloud AI
GOOGLE_APPLICATION_CREDENTIALS=service_account.json
VERTEX_AI_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1

# API Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DEBUG=true
```

## 🤖 AI Models & Services

### Supported AI Models
- **Gemini 2.0 Flash**: Fast inference for real-time analysis
- **Gemini 2.5 Flash**: Advanced reasoning for complex queries
- **Text Embedding Models**: Semantic similarity and clustering

### AI Capabilities
- **Paper Analysis**: Automated extraction of key insights
- **Hypothesis Generation**: AI-driven research hypothesis creation
- **Semantic Search**: Context-aware paper discovery
- **Knowledge Graph**: Relationship extraction between concepts

## 🧪 Development

### Running Tests
```powershell
# Backend tests
cd backend
pytest

# Frontend tests  
cd frontend
npm test
```

### Code Quality
```powershell
# Python formatting
black backend/
flake8 backend/

# TypeScript linting
cd frontend
npm run lint
```

## 📈 Performance & Scalability

- **Async Processing**: Non-blocking I/O for high concurrency
- **Vector Search**: Optimized similarity search with pgvector
- **Caching**: Intelligent caching for frequently accessed papers
- **3D Optimization**: WebGL-based rendering with Three.js optimizations

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- Code style and standards
- Testing requirements
- Pull request process
- Issue reporting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Hackathon Project

This project was developed during a 24-hour NASA hackathon, demonstrating the power of rapid prototyping with modern AI and visualization technologies.

## 📞 Support

For questions and support:
- 📧 Email: your-email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/Galaxy-of-Knowledge/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-username/Galaxy-of-Knowledge/discussions)

---

<div align="center">

**🌌 Explore the Galaxy of Knowledge - Where Research Meets Innovation 🚀**

Made with ❤️ for the scientific community

</div> 
