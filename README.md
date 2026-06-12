# AI Personal Code Editor with Real-Time Execution

An interactive, web-based code editor featuring real-time code execution, persistent console output streaming, and an asynchronous task pipeline. The system utilizes **Django Channels** and **Daphne** to manage full-duplex WebSocket connections and integrates **Celery** capabilities for offloading code compilation tasks seamlessly.

---

## 🚀 Key Features
* **Monaco Editor Integration:** Full-featured workspace offering syntax highlighting, real-time code tracking, and custom console outputs.
* **Sub-Second Streaming:** Instant execution outputs delivered directly across live WebSocket channels.
* **Hybrid Execution Architecture:** Supports distributed network clusters using Redis or a completely self-contained, high-performance In-Memory processing pipeline.
* **Robust Sandbox Error Handling:** Traps standard output (`stdout`) and compilation run crashes gracefully, returning clear debug stacks to the client browser.

---

## 🛠️ Project Structure

```text
AI-Personal-Code-Editor/         <-- Root Project Directory
│
├── editor/                      <-- Project Configuration Package
│   ├── __init__.py
│   ├── asgi.py                  <-- Handles ASGI Protocol & Websocket Routing
│   ├── settings.py              <-- System Environment & Engine Settings
│   └── urls.py                  <-- Core Routing Map
│
├── main/                        <-- Application Workspace Package
│   ├── consumer.py              <-- Handles WebSocket Handshaking & Task Routing
│   ├── tasks.py                 <-- Dynamic Execution Engine (exec/eval logic)
│   └── routing.py               <-- WebSocket URL Mapping Patterns
│
├── my_celery.py                 <-- Celery Application Infrastructure Setup
└── manage.py                    <-- Django Management CLI Entry point