import requests
import json
import os
from datetime import datetime

# ============ CONFIGURAÇÃO ============
ACCESS_TOKEN = "SEU_TOKEN_AQUI"  # ← COLE SEU TOKEN
ACCOUNT_ID = "f8aad5c7-266c-408a-a711-cf407f1720e7"
HISTORICO_FILE = r"C:\frameio_integracao\scripts\historico_uploads.json"
# ======================================

# Tenta importar DaVinci Resolve API
try:
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")
    if not resolve:
        print("❌ DaVinci Resolve não está rodando")
        sys.exit(1)
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    print("✅ Conectado ao DaVinci Resolve")
except ImportError:
    print("❌ Este script deve rodar DENTRO do DaVinci Resolve")
    print("   Coloque na pasta Utility e execute pelo menu Workspace > Scripts")
    sys.exit(1)

def carregar_historico():
    """Carrega o histórico de uploads"""
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, 'r') as f:
            return json.load(f)
    return {"uploads": [], "ultimo": None}

def listar_uploads_para_escolha(historico):
    """Mostra os uploads e deixa usuário escolher"""
    if not historico["uploads"]:
        print("📭 Nenhum upload encontrado no histórico.")
        return None
    
    print("\n📋 VÍDEOS DISPONÍVEIS:")
    print("-" * 60)
    for i, up in enumerate(historico["uploads"][-10:], 1):
        marcador = "▶️" if up["file_id"] == historico["ultimo"] else "  "
        print(f"{marcador} {i}. {up['nome']}")
        print(f"     ID: {up['file_id']}")
        print(f"     Data: {up['data']}")
    print("-" * 60)
    
    escolha = input("\nDigite o número do vídeo (Enter para último): ").strip()
    
    if escolha == "":
        # Usa o último
        for up in historico["uploads"]:
            if up["file_id"] == historico["ultimo"]:
                return up
    else:
        try:
            idx = int(escolha) - 1
            return historico["uploads"][-10:][idx]
        except:
            print("❌ Opção inválida")
            return None
    
    return None

def buscar_comentarios(file_id):
    """Busca comentários no Frame.io"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    url = f"https://api.frame.io/v4/files/{file_id}/comments"
    print(f"\n🔍 Buscando comentários para File ID: {file_id}")
    
    r = requests.get(url, headers=headers)
    
    if r.status_code != 200:
        print(f"❌ Erro: {r.status_code}")
        print(r.text)
        return None
    
    return r.json().get("data", [])

def adicionar_marcadores_na_timeline(comentarios, nome_video):
    """Adiciona marcadores no timeline do DaVinci"""
    if not comentarios:
        print("📭 Nenhum comentário encontrado.")
        return
    
    if not timeline:
        print("❌ Nenhuma timeline aberta")
        return
    
    # Remove marcadores existentes? (opcional)
    # timeline.DeleteMarkersByColor("All")
    
    adicionados = 0
    for comment in comentarios:
        # Pega o frame do comentário (se houver timestamp)
        timestamp = comment.get("timestamp", 0)
        if timestamp > 0:
            frame = int(timestamp * timeline.GetSetting("timelineFrameRate"))
        else:
            frame = 1  # fallback
        
        # Define cor baseada no texto (simples)
        text = comment.get("text", "").lower()
        if "aprov" in text or "ok" in text:
            cor = "Green"
        elif "ajust" in text or "corrig" in text or "erro" in text:
            cor = "Red"
        else:
            cor = "Yellow"
        
        # Formata o nome do marcador
        owner = comment.get("owner", {}).get("name", "Desconhecido")
        nome_marcador = f"{owner}: {text[:50]}..."
        
        # Adiciona marcador
        timeline.AddMarker(frame, cor, "", nome_marcador, 1, "")
        adicionados += 1
        
        # Se tiver respostas, adiciona como marcadores próximos
        for reply in comment.get("replies", []):
            reply_owner = reply.get("owner", {}).get("name", "Desconhecido")
            reply_text = reply.get("text", "")
            reply_nome = f"↳ {reply_owner}: {reply_text[:50]}..."
            timeline.AddMarker(frame + 5, "Blue", "", reply_nome, 1, "")
            adicionados += 1
    
    print(f"✅ {adicionados} marcador(es) adicionado(s) na timeline!")
    print(f"📌 Vá para a timeline e pressione 'M' para ver os marcadores")

# ============ EXECUÇÃO PRINCIPAL ============
if __name__ == "__main__":
    print("=" * 60)
    print("🎬 IMPORTADOR DE COMENTÁRIOS FRAME.IO")
    print("=" * 60)
    
    # 1. Carrega histórico
    historico = carregar_historico()
    
    # 2. Escolhe o vídeo
    video_escolhido = listar_uploads_para_escolha(historico)
    if not video_escolhido:
        print("❌ Nenhum vídeo selecionado")
        sys.exit(1)
    
    print(f"\n🎥 Vídeo selecionado: {video_escolhido['nome']}")
    
    # 3. Busca comentários
    comentarios = buscar_comentarios(video_escolhido['file_id'])
    
    if comentarios is not None:
        # 4. Adiciona na timeline
        adicionar_marcadores_na_timeline(comentarios, video_escolhido['nome'])
    
    input("\nPressione Enter para sair...")