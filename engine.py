import os
import math
import requests
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Charge les secrets depuis le fichier .env
load_dotenv()

# ==========================================
# 1. LOGIQUE MATHÉMATIQUE (LONG ONLY)
# ==========================================

def calc_taille_pos(capital, risque, entree, sl):
    argent_risque = capital * risque
    if entree == sl:
        return 0
    return argent_risque / abs(entree - sl)

def calc_take_profit(entree, sl):
    distance_sl = abs(entree - sl)
    return entree + (distance_sl * 2.5)

# ==========================================
# 2. MOTEUR D'EXÉCUTION BLOCKCHAIN
# ==========================================

def execute_xau_long(prix_entree: float, prix_sl: float):
    # Paramètres stricts de l'usine
    RISQUE = 0.05
    COIN = "xyz:GOLD" # Le vrai Ticker HIP-3
    
    print("\n" + "="*40)
    print("🚀 DÉMARRAGE DE LA SÉQUENCE D'EXÉCUTION HIP-3 🚀")
    print("="*40)

    # --- Étape A : Lecture du Capital Dynamique (Sur Trade.xyz) ---
    adresse_principale = os.getenv("HL_USER_ADDRESS")
    
    try:
        print("📡 Interrogation du sous-réseau HIP-3 pour le solde...")
        url = "https://api.hyperliquid.xyz/info"
        payload = {"type": "clearinghouseState", "user": adresse_principale, "dex": "xyz"}
        res_xyz = requests.post(url, json=payload).json()
        
        capital_dynamique = float(res_xyz["marginSummary"]["accountValue"])
        print(f"💰 Capital actuel détecté : {capital_dynamique:.2f} USDC")
    except Exception as e:
        print(f"❌ Impossible de lire le solde : {e}")
        return False

    # --- Étape B : Calcul des Niveaux ---
    taille = round(calc_taille_pos(capital_dynamique, RISQUE, prix_entree, prix_sl), 3)
    prix_tp = round(calc_take_profit(prix_entree, prix_sl), 1)
    prix_sl = round(prix_sl, 1)

    print(f"📐 Paramètres calculés :")
    print(f"   - Taille (Size) : {taille} {COIN}")
    print(f"   - Entrée max    : {prix_entree}")
    print(f"   - Stop Loss     : {prix_sl}")
    print(f"   - Take Profit   : {prix_tp}")

    # --- Étape C : Connexion à l'Agent et PATCH HIP-3 ---
    secret_key = os.getenv("HL_AGENT_SECRET")
    agent_address = os.getenv("HL_AGENT_ADDRESS")
    
    account = Account.from_key(secret_key)
    exchange = Exchange(account, constants.MAINNET_API_URL, account_address=agent_address)

    # 💉 L'Injection en mémoire (Forçage du SDK)
    exchange.info.name_to_coin[COIN] = 3
    exchange.info.coin_to_asset[3] = 3

    # --- Étape D : Calibration du Levier ---
    print("⚙️ Configuration du levier à x25...")
    try:
        exchange.update_leverage(25, COIN)
    except Exception as e:
        print(f"⚠️ Avertissement levier : {e}")

    # --- Étape E : L'Entrée au Marché (Market Buy via IOC) ---
    prix_achat_max = round(prix_entree * 1.01, 1)
    print(f"📈 Envoi de l'ordre d'achat (Limite IOC à {prix_achat_max})...")
    
    res_entree = exchange.order(
        COIN, 
        is_buy=True, 
        sz=taille, 
        limit_px=prix_achat_max, 
        order_type={"limit": {"tif": "Ioc"}}
    )
    
    if res_entree["status"] != "ok":
        print("❌ Erreur lors de l'achat :", res_entree)
        return False

    print("✅ Position LONG ouverte avec succès !")

    # --- Étape F : Placement des Sécurités (Reduce-Only) ---
    print("🛡️ Placement des sécurités (SL / TP)...")
    
    res_sl = exchange.order(
        COIN,
        is_buy=False,
        sz=taille,
        limit_px=prix_sl,
        order_type={"trigger": {"isMarket": True, "triggerPx": prix_sl, "tpsl": "sl"}},
        reduce_only=True
    )
    
    res_tp = exchange.order(
        COIN,
        is_buy=False,
        sz=taille,
        limit_px=prix_tp,
        order_type={"trigger": {"isMarket": True, "triggerPx": prix_tp, "tpsl": "tp"}},
        reduce_only=True
    )
    
    if res_sl["status"] == "ok" and res_tp["status"] == "ok":
        print("✅ Usine sécurisée. Opération terminée.")
        print("="*40 + "\n")
        return True
    else:
        print("⚠️ Position ouverte mais erreur sur la couverture SL/TP.")
        print("SL Status:", res_sl)
        print("TP Status:", res_tp)
        return False