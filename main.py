from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from engine import execute_xau_long

load_dotenv()
app = FastAPI()

class WebhookPayload(BaseModel):
    passphrase: str

@app.post("/webhook")
async def receive_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    mot_de_passe_attendu = os.getenv("WEBHOOK_PASSPHRASE")
    
    if payload.passphrase != mot_de_passe_attendu:
        raise HTTPException(status_code=403, detail="Accès refusé : Mot de passe incorrect")
    
    print("\n🔔 [WEBHOOK REÇU] Signal d'achat déclenché par TradingView !")

    background_tasks.add_task(execute_xau_long)
    
    return {"status": "success", "message": "Ordre d'achat autonome initié"}

@app.get("/")
async def health_check():
    return {"status": "Usine en ligne et prete a tirer"}