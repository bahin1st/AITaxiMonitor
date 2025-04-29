# 🚖 AITaxiMonitor

This repository provides a practical implementation of anomaly detection in taxi driving behavior.  
It includes simulation tools, real-time monitoring, alerting via APIs, and insights for dispatchers — all powered by smart AI models.

This open-source project aims to assist engineers and researchers in applying AI-driven techniques in transportation safety.

---

## 🚀 Getting Started (Local Setup)

Follow the steps below to run this project locally.

---

### 🔧 1. Set Up Virtual Environment

Create and activate a virtual environment (recommended), then install dependencies:

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt


```
---
# Server to user to have Websockets
daphne -b 127.0.0.1 -p 8000 safetaxi.asgi:application
---
# Orientation views


