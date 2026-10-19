#!/usr/bin/env python3
"""
⚡ EsprieAether - JARVIS API (Minimal Version)
FastAPI backend for the JARVIS OSINT system.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging

app = FastAPI(title="JARVIS OSINT Backend", version="1.0.0")

@app.get("/")
def root():
    return {"status": "ok", "service": "JARVIS OSINT Backend", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "JARVIS OSINT"}

@app.get("/api/status")
def status():
    return {
        "service": "JARVIS OSINT",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "capture": "/api/capture",
            "identify": "/api/identify",
            "person": "/api/person",
            "talk": "/api/talk",
            "pipeline": "/api/pipeline"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
