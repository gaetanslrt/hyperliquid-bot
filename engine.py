import os
import math
import requests
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

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

def execute_xau_long(prix_tv_entree: float, prix_tv_sl: float):
    RISQUE = 0.05
    COIN = "xyz:GOLD" 
    
    print("\n" + "="*40)
    print("🚀 DÉMARRAGE SÉQUENCE : MARKET EXECUTION 🚀")
    print("="*40)

    # --- Étape A : Lecture du Capital ---
    adresse_principale = os.getenv("HL_USER_ADDRESS")
    try:
        url = "https://api.hyperliquid.xyz/info"
        res_xyz = requests.post(url, json={"type": "clearinghouseState", "user": adresse_principale, "dex": "xyz"}).json()
        capital_dynamique = float(res_xyz["marginSummary"]["accountValue"])
    except Exception as e:
        print(f"❌ Impossible de lire le solde : {e}")
        return False

    # --- Étape B : L'Oracle de Prix (Lecture du Carnet d'Ordres HL) ---
    try:
        print("📡 Lecture du prix en temps réel sur Hyperliquid...")
        res_book = requests.post(url, json={"type": "l2Book", "coin": COIN}).json()
        # levels[1][0] correspond au meilleur prix de vente (Best Ask) disponible
        vrai_prix_hl = float(res_book["levels"][1][0]["px"])
        print(f"📊 Décalage détecté -> Prix TV : {prix_tv_entree} | Vrai Prix HL : {vrai_prix_hl}")
    except Exception as e:
        print(f"❌ Impossible de lire le carnet d'ordres : {e}")
        return False

    # --- Étape C : Transposition Mathématique ---
    # On récupère la taille du stop loss imposée par ton indicateur TV
    distance_sl_tv = abs(prix_tv_entree - prix_tv_sl)
    
    # On applique cette distance au vrai prix Hyperliquid
    vrai_sl_hl = round(vrai_prix_hl - distance_sl_tv, 1)
    vrai_tp_hl = round(calc_take_profit(vrai_prix_hl, vrai_sl_hl), 1)
    
    # On calcule la taille avec les vraies données
    taille = round(calc_taille_pos(capital_dynamique, RISQUE, vrai_prix_hl, vrai_sl_hl), 3)

    print(f"📐 Paramètres transposés :")
    print(f"   - Taille (Size) : {taille} {COIN}")
    print(f"   - Vrai SL       : {vrai_sl_hl}")
    print(f"   - Vrai TP       : {vrai_tp_hl}")

    # --- Étape D : Connexion à l'Agent et PATCH HIP-3 ---
    secret_key = os.getenv("HL_AGENT_SECRET")
    agent_address = os.getenv("HL_AGENT_ADDRESS")
    
    account = Account.from_key(secret_key)
    exchange = Exchange(account, constants.MAINNET_API_URL, account_address=agent_address)

    exchange.info.name_to_coin[COIN] = 3
    exchange.info.coin_to_asset[3] = 3

    # --- Étape E : Calibration du Levier ---
    try:
        exchange.update_leverage(25, COIN)
    except Exception as e:
        pass

    # --- Étape F : L'Entrée Forcée (True Market Buy) ---
    # Pour garantir que l'ordre passe peu importe la volatilité de la milliseconde,
    # on fixe un prix limite 5% au-dessus du marché. L'algorithme d'Hyperliquid 
    # te donnera quand même le meilleur prix possible, mais ne bloquera pas l'ordre.
    prix_achat_max = round(vrai_prix_hl * 1.05, 1) 
    print(f"📈 Envoi de l'ordre au marché (Slippage max toléré : {prix_achat_max})...")
    
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

    print("✅ Position LONG ouverte au prix du marché HL !")

    # --- Étape G : Placement des Sécurités (Reduce-Only) ---
    print("🛡️ Placement des sécurités transposées...")
    
    exchange.order(
        COIN,
        is_buy=False,
        sz=taille,
        limit_px=vrai_sl_hl,
        order_type={"trigger": {"isMarket": True, "triggerPx": vrai_sl_hl, "tpsl": "sl"}},
        reduce_only=True
    )
    
    exchange.order(
        COIN,
        is_buy=False,
        sz=taille,
        limit_px=vrai_tp_hl,
        order_type={"trigger": {"isMarket": True, "triggerPx": vrai_tp_hl, "tpsl": "tp"}},
        reduce_only=True
    )
    
    print("✅ Usine sécurisée. Opération terminée.")
    print("="*40 + "\n")
    return True