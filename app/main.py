from fastapi import FastAPI

app = FastAPI(title="Invoice & Payment Tracker API")

@app.get("/")
def read_root():
    return {"message": "Invoice & Payment Tracker API is running"}

@app.get("/health")
def health_check():
    return {"status":"ok"}