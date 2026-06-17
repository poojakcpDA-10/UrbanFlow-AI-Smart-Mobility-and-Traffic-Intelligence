# UrbanFlow AI: Smart Mobility and Traffic Intelligence

## Overview

UrbanFlow AI is an AI-powered smart traffic management and mobility intelligence platform designed to improve urban transportation efficiency through real-time traffic monitoring, vehicle detection, congestion forecasting, and adaptive signal control.

The system combines Computer Vision, Deep Learning, and Predictive Analytics to help city planners and traffic authorities make data-driven decisions for reducing congestion and optimizing traffic flow.

---

## Features

### Vehicle Detection using Vision Transformer (ViT)

* Detects and counts vehicles from traffic camera feeds.
* Achieves approximately **85% detection accuracy** on a custom traffic dataset.
* Supports real-time traffic monitoring and analytics.

### Traffic Forecasting using TCN

* Uses Temporal Convolutional Networks (TCN) to predict traffic density.
* Forecasts future congestion levels based on historical traffic patterns.
* Enables proactive traffic management.

### Adaptive Signal Control

* Dynamically adjusts traffic signal timing based on predicted traffic conditions.
* Helps reduce waiting times and improve traffic flow.

### Interactive Traffic Dashboard

* Real-time traffic analytics and monitoring.
* Interactive congestion visualization.
* Traffic trend analysis and forecasting.

### Smart Maps and Visualization

* Interactive map integration using Leaflet.js.
* Live traffic monitoring and location-based analytics.
* Route and congestion visualization.

### Voice-Controlled Dashboard

* Hands-free operation using Web Speech API.
* Voice commands for navigation and analytics access.

---

## System Architecture

1. Traffic camera feeds are captured.
2. Vision Transformer (ViT) detects and classifies vehicles.
3. Vehicle count and traffic data are stored in PostgreSQL.
4. Temporal Convolutional Network (TCN) predicts future traffic density.
5. Adaptive signal recommendations are generated.
6. Results are displayed through an interactive dashboard.

---

## Tech Stack

### Backend

* Python
* Flask
* REST API

### AI & Machine Learning

* PyTorch
* Vision Transformer (ViT)
* Temporal Convolutional Network (TCN)

### Database

* PostgreSQL

### Frontend

* HTML
* CSS
* JavaScript
* Chart.js
* Leaflet.js

### Additional Technologies

* Docker
* Docker Compose
* Web Speech API

---

## Project Structure

```text
smart_traffic/
│
├── ai_models/
├── backend/
├── database/
├── frontend/
├── nginx/
├── uploads/
├── app.py
├── run.py
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Installation

### Clone Repository

```bash
git clone https://github.com/poojakcpDA-10/UrbanFlow-AI-Smart-Mobility-and-Traffic-Intelligence.git
cd UrbanFlow-AI-Smart-Mobility-and-Traffic-Intelligence
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python run.py
```

The application will start on:

```text
http://localhost:5000
```

---

## Docker Deployment

Build and start containers:

```bash
docker-compose up --build
```

Run in background:

```bash
docker-compose up -d
```

Stop containers:

```bash
docker-compose down
```

---

## Results

* ~85% Vehicle Detection Accuracy
* Real-Time Traffic Monitoring
* Traffic Density Forecasting
* Congestion Analysis and Visualization
* Adaptive Signal Recommendations
* Voice-Controlled Dashboard

---

## Applications

* Smart Cities
* Intelligent Transportation Systems (ITS)
* Urban Traffic Monitoring
* Traffic Signal Optimization
* Congestion Prediction
* Mobility Analytics
* Transportation Planning

---

## Future Enhancements

* Multi-camera traffic monitoring
* Emergency vehicle prioritization
* Accident detection and alerts
* Integration with IoT traffic sensors
* Mobile application support
* AI-powered route optimization

---

## Author

**Pooja K C**

AI | Machine Learning | Computer Vision | Data Science

---

## License

This project is developed for educational, research, and smart-city innovation purposes.
