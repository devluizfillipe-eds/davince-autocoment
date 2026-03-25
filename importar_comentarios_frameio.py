import requests
import json
import os
import sys

# ============ CONFIGURAÇÃO ============
ACCESS_TOKEN = "Acesstoken"  # ← COLE SEU TOKEN
ACCOUNT_ID = "Accountid"  # ← COLE SEU ACCOUNT ID
# ======================================

print("=" * 60)
print("🎬 IMPORTADOR DE COMENTÁRIOS FRAME.IO")
print("=" * 60)

# ============ CONEXÃO COM DAVINCI RESOLVE ============
try:
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")
    
    if not resolve:
        print("❌ Não foi possível conectar ao DaVinci Resolve")
        print("   👉 Verifique se o programa está aberto")
        sys.exit(1)
    
    print("✅ API do DaVinci encontrada")
    
    project_manager = resolve.GetProjectManager()
    if not project_manager:
        print("❌ Não foi possível acessar o Project Manager")
        sys.exit(1)
    
    project = project_manager.GetCurrentProject()
    if not project:
        print("❌ Nenhum projeto aberto")
        print("   👉 Abra um projeto primeiro")
        sys.exit(1)
    
    print(f"✅ Projeto atual: {project.GetName()}")
    
    timeline = project.GetCurrentTimeline()
    if not timeline:
        print("❌ Nenhuma timeline ativa")
        print("   👉 Crie uma timeline ou clique em uma existente")
        sys.exit(1)
    
    print(f"✅ Timeline ativa: {timeline.GetName()}")
    fps = float(timeline.GetSetting("timelineFrameRate"))
    print(f"   Frame rate: {fps} fps")

except ImportError:
    print("❌ Script deve ser executado dentro do DaVinci Resolve")
    sys.exit(1)

print("-" * 60)

# ============ LOCALIZAR ARQUIVO DE MAPEAMENTO ============
mapeamento_path = r"C:\frameio_integracao\scripts\mapeamento_videos.json"

if not os.path.exists(mapeamento_path):
    print(f"❌ Arquivo de mapeamento não encontrado: {mapeamento_path}")
    print("   👉 Execute o script de upload primeiro")
    sys.exit(1)

print(f"📁 Mapeamento encontrado: {mapeamento_path}")

with open(mapeamento_path, 'r') as f:
    mapeamento = json.load(f)

# ============ IDENTIFICAR VÍDEO NA TIMELINE ============
clipes = timeline.GetItemListInTrack("video", 1)

if not clipes:
    print("❌ Nenhum clipe encontrado na timeline")
    sys.exit(1)

clip = clipes[0]
media_item = clip.GetMediaPoolItem()

if not media_item:
    print("❌ Não foi possível obter o MediaPoolItem do clipe")
    sys.exit(1)

caminho_video = media_item.GetClipProperty("File Path")

if not caminho_video:
    print("❌ Não foi possível obter o caminho do vídeo")
    sys.exit(1)

print(f"\n🎥 Vídeo na timeline: {os.path.basename(caminho_video)}")
print(f"📁 Caminho: {caminho_video}")

# ============ BUSCAR FILE_ID NO MAPEAMENTO ============
if caminho_video not in mapeamento:
    print(f"\n❌ Vídeo não encontrado no mapeamento")
    print("   👉 Execute o script de upload para este vídeo primeiro")
    sys.exit(1)

file_id = mapeamento[caminho_video]
print(f"\n📌 File ID encontrado: {file_id}")

# ============ BUSCAR COMENTÁRIOS NO FRAME.IO ============
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

url = f"https://api.frame.io/v4/accounts/{ACCOUNT_ID}/files/{file_id}/comments"

print("\n🔍 Buscando comentários...")

try:
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"❌ Erro na API: {r.status_code}")
        if r.status_code == 404:
            print("   Nenhum comentário encontrado para este vídeo")
        sys.exit(1)
    
    comentarios = r.json().get("data", [])
    print(f"✅ {len(comentarios)} comentário(s) encontrado(s)")
    
except Exception as e:
    print(f"❌ Erro na requisição: {e}")
    sys.exit(1)

# ============ ADICIONAR MARCADORES NA TIMELINE ============
if not comentarios:
    print("\n📭 Nenhum comentário para adicionar")
    sys.exit(0)

frame_inicial = int(timeline.GetStartFrame())
frame_final = int(timeline.GetEndFrame())
duracao_frames = frame_final - frame_inicial

print(f"\n   Frame inicial: {frame_inicial}")
print(f"   Frame final: {frame_final}")
print(f"   Duração do vídeo: {duracao_frames} frames")

adicionados = 0
falhas = 0

for i, comment in enumerate(comentarios, 1):
    try:
        timestamp = comment.get('timestamp', 0)
        texto = comment.get('text', 'Sem texto')
        
        # Ajusta timestamp se estiver fora da duração
        if timestamp < 0:
            timestamp = 0
        elif timestamp >= duracao_frames:
            print(f"   ⚠️ Comentário {i}: frame {timestamp} além da duração")
            timestamp = duracao_frames - 1
        
        # Define cor baseada no texto
        texto_lower = texto.lower()
        if any(p in texto_lower for p in ['aprov', 'ok', '👍', '✅', 'nice']):
            cor = "Green"
        elif any(p in texto_lower for p in ['ajust', 'corrig', 'erro', 'fix', 'problema']):
            cor = "Red"
        else:
            cor = "Yellow"
        
        # Adiciona marcador
        resultado = timeline.AddMarker(timestamp, cor, "FrameioComment", texto, 1, "")
        
        if resultado:
            adicionados += 1
            print(f"   ✅ Marcador {i} adicionado no frame {timestamp} ({timestamp/fps:.2f}s)")
        else:
            falhas += 1
            print(f"   ❌ Falha ao adicionar marcador {i}")
            
    except Exception as e:
        falhas += 1
        print(f"   ❌ Erro no comentário {i}: {e}")

print(f"\n✅ {adicionados} marcador(es) adicionado(s)!")
if falhas:
    print(f"❌ {falhas} falha(s)")

print("\n✅ Script finalizado!")