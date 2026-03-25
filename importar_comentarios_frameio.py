import requests
import json
import os
import sys

# ============ CONFIGURAÇÃO (EDITAR APENAS AQUI) ============
ACCESS_TOKEN = "<YOUR_ACCESS_TOKEN>"
ACCOUNT_ID = "<YOUR_ACCOUNT_ID>"
# ============================================================

# ============ CONEXÃO COM DAVINCI RESOLVE ============
resolve = None
project = None
timeline = None

print("=" * 60)
print("🎬 IMPORTADOR DE COMENTÁRIOS FRAME.IO")
print("=" * 60)

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
def localizar_mapeamento():
    """Procura o arquivo de mapeamento em locais conhecidos"""
    
    # Possíveis locais
    possiveis_locais = [
        r"C:\frameio_integracao\scripts\mapeamento_videos.json",
        os.path.join(os.path.expanduser("~"), "frameio_integracao", "scripts", "mapeamento_videos.json")
    ]
    
    # Tenta obter o diretório do script por outros métodos
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possiveis_locais.insert(1, os.path.join(script_dir, "mapeamento_videos.json"))
    except NameError:
        # __file__ não está definido no ambiente do DaVinci
        pass
    
    for caminho in possiveis_locais:
        if os.path.exists(caminho):
            print(f"📁 Mapeamento encontrado: {caminho}")
            return caminho
    
    print("❌ Arquivo de mapeamento não encontrado")
    print("   👉 Execute o script de upload primeiro para gerar o mapeamento")
    return None

# ============ IDENTIFICAR VÍDEO NA TIMELINE ============
def obter_caminho_video_timeline():
    """Obtém o caminho do arquivo de vídeo do primeiro clipe da timeline"""
    
    # Tenta obter clipes da primeira trilha de vídeo
    clipes = timeline.GetItemListInTrack("video", 1)
    
    if not clipes:
        print("❌ Nenhum clipe encontrado na timeline")
        return None
    
    # Pega o primeiro clipe
    clipe = clipes[0]
    
    # Tenta diferentes formas de obter o caminho
    caminho = None
    
    # Método 1: File Path
    caminho = clipe.GetProperty("File Path")
    if caminho:
        print(f"🎥 Vídeo identificado: {os.path.basename(caminho)}")
        print(f"📁 Caminho: {caminho}")
        return caminho
    
    # Método 2: Path
    caminho = clipe.GetProperty("Path")
    if caminho:
        print(f"🎥 Vídeo identificado: {os.path.basename(caminho)}")
        print(f"📁 Caminho: {caminho}")
        return caminho
    
    # Método 3: Clip Name (apenas nome, não caminho completo)
    nome = clipe.GetProperty("Clip Name")
    if nome:
        print(f"⚠️ Apenas o nome do clipe foi encontrado: {nome}")
        print("   O script precisa do caminho completo do arquivo")
        print("   Certifique-se de que o clipe é um arquivo de mídia local")
    
    print("❌ Não foi possível obter o caminho do vídeo")
    print("   Verifique se o clipe é um arquivo de mídia (não um título ou gerador)")
    return None

# ============ BUSCAR COMENTÁRIOS NO FRAME.IO ============
def buscar_comentarios(file_id):
    """Busca comentários no Frame.io"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    url = f"https://api.frame.io/v4/accounts/{ACCOUNT_ID}/files/{file_id}/comments"

    print(f"\n🔍 Buscando comentários para o vídeo...")

    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"❌ Erro na API: {r.status_code}")
            if r.status_code == 404:
                print("   Nenhum comentário encontrado para este vídeo")
            return []
        comentarios = r.json().get("data", [])
        print(f"✅ {len(comentarios)} comentário(s) encontrado(s)")
        return comentarios
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return []

# ============ ADICIONAR MARCADORES NA TIMELINE ============
def adicionar_marcadores(comentarios, timeline, fps):
    """Adiciona marcadores na timeline usando timestamps em FRAMES"""
    if not comentarios:
        print("\n📭 Nenhum comentário para adicionar.")
        return

    try:
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
                # Timestamp da API V4 está em FRAMES
                timestamp_frames = comment.get('timestamp', 0)
                texto = comment.get('text', 'Sem texto')

                # Verifica se está dentro da duração
                frame_relativo = timestamp_frames
                if frame_relativo < 0:
                    frame_relativo = 0
                elif frame_relativo >= duracao_frames:
                    print(f"   ⚠️ Comentário {i}: frame {timestamp_frames} além da duração")
                    frame_relativo = duracao_frames - 1

                # Define cor baseada no texto
                texto_lower = texto.lower()
                if any(p in texto_lower for p in ['aprov', 'ok', '👍', '✅', 'nice']):
                    cor = "Green"
                elif any(p in texto_lower for p in ['ajust', 'corrig', 'erro', 'fix', 'problema']):
                    cor = "Red"
                else:
                    cor = "Yellow"

                # Adiciona marcador
                resultado = timeline.AddMarker(frame_relativo, cor, "FrameioComment", texto, 1, "")

                if resultado:
                    adicionados += 1
                    print(f"   ✅ Marcador {i} adicionado no frame {frame_relativo} ({frame_relativo/fps:.2f}s)")
                else:
                    falhas += 1
                    print(f"   ❌ Falha ao adicionar marcador {i}")

            except Exception as e:
                falhas += 1
                print(f"   ❌ Erro no comentário {i}: {e}")

        print(f"\n✅ {adicionados} marcador(es) adicionado(s)!")
        if falhas:
            print(f"❌ {falhas} falha(s)")

    except Exception as e:
        print(f"❌ Erro ao adicionar marcadores: {e}")

# ============ EXECUÇÃO PRINCIPAL ============

# 1. Localizar arquivo de mapeamento
caminho_mapeamento = localizar_mapeamento()
if not caminho_mapeamento:
    sys.exit(1)

# 2. Carregar mapeamento
with open(caminho_mapeamento, 'r') as f:
    mapeamento = json.load(f)

# 3. Identificar vídeo na timeline
caminho_video = obter_caminho_video_timeline()
if not caminho_video:
    print("\n❌ Não foi possível identificar o vídeo na timeline")
    sys.exit(1)

# 4. Buscar file_id no mapeamento
if caminho_video not in mapeamento:
    print(f"\n❌ Vídeo não encontrado no mapeamento")
    print(f"   Execute o script de upload para este vídeo primeiro")
    sys.exit(1)

file_id = mapeamento[caminho_video]
print(f"\n📌 File ID encontrado: {file_id}")

# 5. Buscar comentários
comentarios = buscar_comentarios(file_id)

# 6. Adicionar marcadores
if comentarios:
    adicionar_marcadores(comentarios, timeline, fps)
else:
    print("\n📭 Nenhum comentário encontrado para este vídeo")

print("\n✅ Script finalizado!")