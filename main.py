import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

# On importe ton usine d'exécution
from engine import execute_xau_long

load_dotenv()

app = FastAPI(title="Terminal Hyperliquid Gold")

# ==========================================
# 1. LE MODÈLE DE DONNÉES (Le Vigile)
# ==========================================
class TradingViewSignal(BaseModel):
    passphrase: str
    entree: float
    sl: float

# ==========================================
# 2. LA ROUTE D'ÉCOUTE
# ==========================================
@app.post("/webhook")
async def webhook_receiver(signal: TradingViewSignal, background_tasks: BackgroundTasks):
    
    # --- A. Sécurité ---
    mot_de_passe_attendu = os.getenv("WEBHOOK_PASSPHRASE")
    if signal.passphrase != mot_de_passe_attendu:
        print("🚨 Tentative d'intrusion bloquée (Mauvais mot de passe)")
        raise HTTPException(status_code=401, detail="Accès refusé")
    
    print(f"\n🔔 [WEBHOOK REÇU] Entrée prévue : {signal.entree} | SL : {signal.sl}")

    # --- B. Exécution Asynchrone ---
    # On confie la tâche de trading à un processus en arrière-plan
    background_tasks.add_task(execute_xau_long, signal.entree, signal.sl)

    # --- C. Réponse Immédiate ---
    # On répond tout de suite à TradingView pour éviter un "Timeout"
    return {"status": "success", "message": "Ordre transféré à l'usine d'exécution"}

# Route de test (pour vérifier que le serveur est en ligne depuis ton navigateur)
@app.get("/")
def read_root():
    return {"status": "online", "system": "Hyperliquid Gold Engine"}

# RUN SERVER
# uvicorn main:app --reload