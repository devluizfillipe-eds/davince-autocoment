import requests
import json
import os

# ============ CONFIGURAÇÃO ============
ACCESS_TOKEN = "SEU_TOKEN_AQUI"
ACCOUNT_ID = "SUA_ACCOUNT_ID_AQUI"
HISTORICO_FILE = r"C:\frameio_integracao\scripts\historico_uploads.json"
# ======================================

# Na versão FREE, as variáveis resolve, fusion e bmd já estão disponíveis
# quando o script é executado pelo menu Workspace [citation:6]
if not 'resolve' in globals():
    print("❌ ERRO: Este script deve ser executado pelo menu Workspace do DaVinci Resolve")
    print("   Vá em: Workspace → Scripts → Utility → importar_comentarios_frameio.py")
    sys.exit()

# Obtém o projeto e timeline atuais
project = resolve.GetProjectManager().GetCurrentProject()
if not project:
    print("❌ Nenhum projeto aberto")
    sys.exit()

timeline = project.GetCurrentTimeline()
if not timeline:
    print("❌ Nenhuma timeline aberta")
    print("   Crie ou abra uma timeline primeiro")
    sys.exit()

print("✅ Conectado ao DaVinci Resolve (Free)")
print(f"   Projeto: {project.GetName()}")
print(f"   Timeline: {timeline.GetName()}")

def carregar_historico():
    """Carrega o histórico de uploads"""
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, 'r') as f:
            return json.load(f)
    return {"uploads": [], "ultimo": None}

def escolher_video(historico):
    """Mostra os uploads e retorna o escolhido"""
    if not historico["uploads"]:
        print("📭 Nenhum upload encontrado no histórico.")
        return None
    
    print("\n📋 VÍDEOS DISPONÍVEIS:")
    print("-" * 60)
    uploads_recentes = historico["uploads"][-10:]
    
    for i, up in enumerate(uploads_recentes, 1):
        marcador = "▶️" if up["file_id"] == historico["ultimo"] else "  "
        print(f"{marcador} {i}. {up['nome']} (ID: {up['file_id'][:8]}...)")
    
    print("-" * 60)
    print("Digite o número do vídeo (Enter para último): ", end="")
    
    try:
        escolha = input().strip()
        if escolha == "":
            for up in historico["uploads"]:
                if up["file_id"] == historico["ultimo"]:
                    return up
        else:
            idx = int(escolha) - 1
            if 0 <= idx < len(uploads_recentes):
                return uploads_recentes[idx]
            else:
                print("Número inválido. Usando último.")
                for up in historico["uploads"]:
                    if up["file_id"] == historico["ultimo"]:
                        return up
    except:
        print("Opção inválida. Usando último.")
        for up in historico["uploads"]:
            if up["file_id"] == historico["ultimo"]:
                return up
    
    return None

def buscar_comentarios(file_id):
    """Busca comentários no Frame.io"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    url = f"https://api.frame.io/v4/files/{file_id}/comments"
    print(f"\n🔍 Buscando comentários...")
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"❌ Erro na API: {r.status_code}")
            return None
        return r.json().get("data", [])
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return None

def adicionar_marcadores(comentarios):
    """Adiciona marcadores na timeline"""
    if not comentarios:
        print("📭 Nenhum comentário encontrado.")
        return
    
    adicionados = 0
    
    for comment in comentarios:
        frame = 1  # posição padrão
        
        # Define cor baseada no texto
        text = comment.get("text", "").lower()
        if "aprov" in text or "ok" in text:
            cor = "Green"
        elif "ajust" in text or "corrig" in text or "erro" in text:
            cor = "Red"
        else:
            cor = "Yellow"
        
        owner = comment.get("owner", {}).get("name", "Desconhecido")
        note = f"{owner}: {comment.get('text', '')}"
        
        timeline.AddMarker(frame, cor, "", note, 1, "")
        adicionados += 1
    
    print(f"\n✅ {adicionados} marcador(es) adicionado(s) na timeline!")

# ============ EXECUÇÃO ============
print("=" * 60)
print("🎬 IMPORTADOR DE COMENTÁRIOS FRAME.IO")
print("=" * 60)

# 1. Carrega histórico
historico = carregar_historico()

# 2. Escolhe o vídeo
video = escolher_video(historico)
if not video:
    print("❌ Nenhum vídeo selecionado")
    sys.exit()

print(f"\n🎥 Vídeo selecionado: {video['nome']}")

# 3. Busca comentários
comentarios = buscar_comentarios(video['file_id'])

# 4. Adiciona na timeline
if comentarios is not None:
    adicionar_marcadores(comentarios)

print("\n✅ Script finalizado!")