import json
import os
import time
import threading
import requests
from datetime import datetime

# ============ CONFIGURAÇÕES ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# Refresh token da conta da empresa (embutido como fallback)
# IMPORTANTE: Substitua pelo seu refresh_token real
REFRESH_TOKEN_FALLBACK = "fr_v2_seu_refresh_token_aqui"

# URLs da API do Frame.io
TOKEN_URL = "https://auth.frame.io/oauth/token"
# =======================================

# Variáveis globais (thread-safe)
_token_cache = None
_token_lock = threading.Lock()
_refresh_thread = None
_thread_running = False


def carregar_config():
    """Carrega a configuração do arquivo JSON"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "access_token": "",
        "refresh_token": REFRESH_TOKEN_FALLBACK,
        "expires_at": 0,
        "account_id": "",
        "folder_id": ""
    }


def salvar_config(config):
    """Salva a configuração no arquivo JSON"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def renovar_token(refresh_token):
    """
    Renova o access_token usando o refresh_token
    Retorna (novo_access_token, novo_refresh_token, expires_in_seconds)
    """
    try:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(TOKEN_URL, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token", refresh_token)  # Alguns fluxos mantém o mesmo
            expires_in = data.get("expires_in", 3600)  # Padrão: 1 hora
            
            return access_token, new_refresh_token, expires_in
        else:
            print(f"[Token Manager] Erro ao renovar token: {response.status_code}")
            print(f"Resposta: {response.text}")
            return None, None, None
            
    except Exception as e:
        print(f"[Token Manager] Exceção ao renovar token: {e}")
        return None, None, None


def verificar_e_renovar():
    """Verifica se o token está perto de expirar e renova se necessário"""
    global _token_cache
    
    config = carregar_config()
    
    agora = int(time.time())
    expires_at = config.get("expires_at", 0)
    tempo_restante = expires_at - agora
    
    # Se faltar menos de 5 minutos (300 segundos) OU já expirou
    if tempo_restante < 300:
        print(f"[Token Manager] Token expira em {tempo_restante} segundos. Renovando...")
        
        refresh_token = config.get("refresh_token")
        if not refresh_token:
            print("[Token Manager] Sem refresh_token. Use o fallback.")
            refresh_token = REFRESH_TOKEN_FALLBACK
        
        novo_token, novo_refresh, expires_in = renovar_token(refresh_token)
        
        if novo_token:
            novo_expires_at = agora + expires_in
            
            config["access_token"] = novo_token
            config["refresh_token"] = novo_refresh or refresh_token
            config["expires_at"] = novo_expires_at
            salvar_config(config)
            
            # Atualiza cache
            with _token_lock:
                _token_cache = novo_token
            
            print(f"[Token Manager] Token renovado! Válido até {datetime.fromtimestamp(novo_expires_at)}")
            return True
        else:
            print("[Token Manager] Falha ao renovar token!")
            return False
    
    return True  # Token ainda válido


def get_token():
    """
    Retorna um token válido.
    Deve ser chamado pelos outros scripts.
    """
    global _token_cache
    
    with _token_lock:
        if _token_cache:
            return _token_cache
    
    config = carregar_config()
    token = config.get("access_token")
    
    if token:
        # Verifica se ainda é válido
        agora = int(time.time())
        expires_at = config.get("expires_at", 0)
        
        if agora < expires_at:
            with _token_lock:
                _token_cache = token
            return token
    
    # Token inválido ou expirado, renova agora
    print("[Token Manager] Token inválido ou expirado. Renovando...")
    refresh_token = config.get("refresh_token", REFRESH_TOKEN_FALLBACK)
    novo_token, novo_refresh, expires_in = renovar_token(refresh_token)
    
    if novo_token:
        agora = int(time.time())
        config["access_token"] = novo_token
        config["refresh_token"] = novo_refresh or refresh_token
        config["expires_at"] = agora + expires_in
        salvar_config(config)
        
        with _token_lock:
            _token_cache = novo_token
        
        return novo_token
    
    print("[Token Manager] Falha crítica ao obter token!")
    return None


def get_account_id():
    """Retorna o account_id do Frame.io"""
    config = carregar_config()
    return config.get("account_id", "")


def get_folder_id():
    """Retorna o folder_id do Frame.io"""
    config = carregar_config()
    return config.get("folder_id", "")


def definir_ids(account_id, folder_id):
    """Define account_id e folder_id (chamado na configuração inicial)"""
    config = carregar_config()
    config["account_id"] = account_id
    config["folder_id"] = folder_id
    salvar_config(config)
    print(f"[Token Manager] IDs salvos: account={account_id}, folder={folder_id}")


def thread_renovacao_background():
    """Thread que roda em background verificando e renovando tokens"""
    global _thread_running
    print("[Token Manager] Thread de renovação iniciada")
    
    while _thread_running:
        time.sleep(60)  # Verifica a cada 1 minuto
        verificar_e_renovar()
    
    print("[Token Manager] Thread de renovação encerrada")


def iniciar_thread():
    """Inicia a thread de renovação em background"""
    global _refresh_thread, _thread_running
    
    if _refresh_thread is None or not _refresh_thread.is_alive():
        _thread_running = True
        _refresh_thread = threading.Thread(target=thread_renovacao_background, daemon=True)
        _refresh_thread.start()
        print("[Token Manager] Thread de renovação iniciada com sucesso")


def parar_thread():
    """Para a thread de renovação (útil ao fechar o Resolve)"""
    global _thread_running
    _thread_running = False
    print("[Token Manager] Solicitado parada da thread de renovação")


# Teste rápido se executar diretamente
if __name__ == "__main__":
    print("=" * 50)
    print("Teste do Token Manager")
    print("=" * 50)
    
    token = get_token()
    if token:
        print(f"✅ Token obtido: {token[:50]}...")
        print(f"✅ Account ID: {get_account_id()}")
        print(f"✅ Folder ID: {get_folder_id()}")
    else:
        print("❌ Falha ao obter token")
    
    # Mostra onde está o config.json
    print(f"\n📁 Arquivo de configuração: {CONFIG_FILE}")