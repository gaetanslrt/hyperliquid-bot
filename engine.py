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
# 2. MOTEUR D'EXÉCUTION BLOCKCHAIN 100% AUTONOME
# ==========================================

def execute_xau_long():
    # --- PARAMÈTRES STRATÉGIQUES FIXES ---
    RISQUE = 0.05
    COIN = "xyz:GOLD" 
    DISTANCE_SL = 10.0  
    LEVIER_MAX = 25     
    TAILLE_MAX = 100.0
    
    print("\n" + "="*40)
    print("🚀 DÉMARRAGE SÉQUENCE : AUTONOMOUS EXECUTION 🚀")
    print("="*40)

    # --- Étape A : L'Oracle d'Infrastructure (ID Global & Précision) ---
    try:
        url = "https://api.hyperliquid.xyz/info"
        dex_name = COIN.split(":")[0] # Extrait "xyz"
        
        print(f"📡 Extraction de l'ADN réseau pour le constructeur '{dex_name}'...")
        
        # 1. Trouver l'index secret du constructeur (perp_dex_index)
        res_dexs = requests.post(url, json={"type": "perpDexs"}).json()
        perp_dex_index = None
        for i, dex in enumerate(res_dexs):
            if dex and dex.get("name") == dex_name:
                perp_dex_index = i
                break
                
        if perp_dex_index is None:
            print(f"❌ Impossible de trouver le constructeur {dex_name} sur la blockchain.")
            return False

        # 2. Trouver l'index local et la précision (szDecimals)
        res_meta = requests.post(url, json={"type": "meta", "dex": dex_name}).json()
        sz_decimals = 0
        local_index = 0
        for i, asset in enumerate(res_meta["universe"]):
            if asset["name"] == COIN:
                sz_decimals = asset["szDecimals"]
                local_index = i
                break
                
        # 3. La Formule Magique HIP-3 pour l'ID Global
        global_asset_id = 100000 + (perp_dex_index * 10000) + local_index
        print(f"🔍 ADN validé -> DEX_Index: {perp_dex_index} | Local_Index: {local_index} | ID_Global: {global_asset_id}")

        # 4. Lecture du capital
        adresse_principale = os.getenv("HL_USER_ADDRESS")
        res_xyz = requests.post(url, json={"type": "clearinghouseState", "user": adresse_principale, "dex": dex_name}).json()
        capital_dynamique = float(res_xyz["marginSummary"]["accountValue"])
        
    except Exception as e:
        print(f"❌ Erreur réseau lors de la lecture d'infrastructure : {e}")
        return False

    # --- Étape B : Lecture du Prix en Temps Réel ---
    try:
        print("📡 Lecture du prix du marché...")
        res_book = requests.post(url, json={"type": "l2Book", "coin": COIN}).json()
        vrai_prix_hl = float(res_book["levels"][1][0]["px"])
    except Exception as e:
        print(f"❌ Impossible de lire le carnet d'ordres : {e}")
        return False

    # --- Étape C : Calculs Absolus et Contraintes ---
    vrai_sl_hl = round(vrai_prix_hl - DISTANCE_SL, 1)
    vrai_tp_hl = round(calc_take_profit(vrai_prix_hl, vrai_sl_hl), 1)
    
    taille_theorique = calc_taille_pos(capital_dynamique, RISQUE, vrai_prix_hl, vrai_sl_hl)
    taille_max_levier = (capital_dynamique * LEVIER_MAX) / vrai_prix_hl
    
    taille_limitee = min(taille_theorique, taille_max_levier, TAILLE_MAX)
    
    if sz_decimals == 0:
        taille = int(taille_limitee)
    else:
        taille = round(taille_limitee, sz_decimals)

    print(f"📐 Paramètres de l'ordre :")
    print(f"   - Taille finale : {taille} {COIN}")
    print(f"   - Entrée prévue : {vrai_prix_hl}")
    print(f"   - Vrai SL       : {vrai_sl_hl} (-{DISTANCE_SL} pts)")
    print(f"   - Vrai TP       : {vrai_tp_hl}")

    # --- Étape D : Connexion à l'Agent et PATCH HIP-3 Dynamique ---
    secret_key = os.getenv("HL_AGENT_SECRET")
    agent_address = os.getenv("HL_AGENT_ADDRESS")
    
    account = Account.from_key(secret_key)
    exchange = Exchange(account, constants.MAINNET_API_URL, account_address=agent_address)

    # 💉 L'Injection Parfaite (Fini le hardcoding)
    exchange.info.name_to_coin[COIN] = local_index
    exchange.info.coin_to_asset[local_index] = global_asset_id
    exchange.info.asset_to_sz_decimals[global_asset_id] = sz_decimals
    exchange.info.asset_to_sz_decimals[local_index] = sz_decimals

    # --- Étape E : Calibration du Levier ---
    try:
        exchange.update_leverage(LEVIER_MAX, COIN)
    except Exception as e:
        pass

    # --- Étape F : L'Entrée Forcée (Market Buy) ---
    prix_achat_max = round(vrai_prix_hl * 1.05, 1) 
    print(f"📈 Envoi de l'ordre au marché...")
    
    res_entree = exchange.order(
        COIN, 
        is_buy=True, 
        sz=taille, 
        limit_px=prix_achat_max, 
        order_type={"limit": {"tif": "Ioc"}}
    )
    
    if res_entree["status"] != "ok":
        print("❌ Erreur Réseau (Signature) :", res_entree)
        return False

    try:
        statut_interne = res_entree["response"]["data"]["statuses"][0]
        if "error" in statut_interne:
            print(f"🛑 REJET DU MARCHÉ : {statut_interne['error']}")
            return False 
    except Exception as e:
        pass

    print("✅ Position LONG ouverte au prix du marché HL !")

    # --- Étape G : Placement des Sécurités (Reduce-Only) ---
    print("🛡️ Placement des sécurités...")
    
    exchange.order(
        COIN, is_buy=False, sz=taille, limit_px=vrai_sl_hl,
        order_type={"trigger": {"isMarket": True, "triggerPx": vrai_sl_hl, "tpsl": "sl"}},
        reduce_only=True
    )
    
    exchange.order(
        COIN, is_buy=False, sz=taille, limit_px=vrai_tp_hl,
        order_type={"trigger": {"isMarket": True, "triggerPx": vrai_tp_hl, "tpsl": "tp"}},
        reduce_only=True
    )
    
    print("✅ Usine sécurisée. Opération terminée.")
    print("="*40 + "\n")
    return True