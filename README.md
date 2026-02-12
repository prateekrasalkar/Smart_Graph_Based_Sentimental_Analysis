# Smart_Graph_Based_Sentimental_Analysis
This project is a smart social network analysis tool that automatically predicts relationships based on content analysis and sentiment analysis.

# Overview

This project models a social network using a graph database (Neo4j) and dynamically predicts relationships between users based on their post content. It also performs basic sentiment analysis and visualizes the entire network using an interactive D3.js force-directed graph.

# The system demonstrates:

Graph data modeling

Content-based similarity detection

Rule-based sentiment analysis

RESTful API development

Real-time interactive visualization

# 🏗️ Architecture
Frontend (HTML + Tailwind + D3.js)
        ↓
Flask REST API (Python)
        ↓
Neo4j Graph Database

# Color-coded nodes based on sentiment:

🟢 Positive

🔴 Negative

⚪ Neutral

Zoom, drag, and dynamic updates

# 🛠️ Tech Stack
Backend

Python 3.x

Flask

Neo4j

Backoff (retry handling)

Frontend

HTML5

Tailwind CSS

Vanilla JavaScript

D3.js

⚙️ Installation Guide
1️⃣ Clone Repository
git clone https://github.com/your-username/smart-social-network-analysis.git
cd smart-social-network-analysis

2️⃣ Install Dependencies
pip install flask flask-cors neo4j backoff

3️⃣ Start Neo4j

Make sure Neo4j is running locally:

bolt://localhost:7687

# Neo4j command after connecting it to database:-
# MATCH ()-[r:SIMILAR_CONTENT]->() RETURN count(r);

If credentials are required, update them in:

Neo4jHandler("bolt://localhost:7687")

4️⃣ Run Backend
python app.py


Server runs on:
http://localhost:5001
