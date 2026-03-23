import requests
import json
import os
import sys
from tkinter import Tk, Listbox, Button, Scrollbar, END, Frame
from datetime import datetime

# ============ CONFIGURAÇÃO (EDITAR APENAS AQUI) ============
ACCESS_TOKEN = "<YOUR_ACCESS_TOKEN>"
FOLDER_ID = "<YOUR_FOLDER_ID>"  # pasta raiz do projeto
# ============================================================

# ============ CONEXÃO COM DAVINCI RESOLVE ============
resolve = None
project = None
timeline = None
modo_console = False

print("=" * 60)
print("🎬 IMPORTADOR DE COMENTÁRIOS FRAME.IO")
print("=" * 60)

try:
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")

    if resolve:
        print("✅ API do DaVinci encontrada")

        project_manager = resolve.GetProjectManager()
        if project_manager:
            project = project_manager.GetCurrentProject()
            if project:
                print(f"✅ Projeto atual: {project.GetName()}")

                timeline = project.GetCurrentTimeline()
                if timeline:
                    print(f"✅ Timeline ativa: {timeline.GetName()}")
                    fps = timeline.GetSetting("timelineFrameRate")
                    print(f"   Frame rate: {fps} fps")
                else:
                    print("❌ Nenhuma timeline ativa")
                    print("   👉 Crie uma timeline ou clique em uma existente")
                    modo_console = True
            else:
                print("❌ Nenhum projeto aberto")
                print("   👉 Abra um projeto primeiro")
                modo_console = True
        else:
            print("❌ Não foi possível acessar o Project Manager")
            modo_console = True
    else:
        print("❌ Não foi possível conectar ao DaVinci Resolve")
        print("   👉 Verifique se o programa está aberto")
        modo_console = True

except ImportError:
    print("⚠️ Executando em modo independente (sem DaVinci)")
    print("   Os comentários serão apenas exibidos no console")
    modo_console = True

if modo_console:
    print("\n⚠️ MODO CONSOLE APENAS (sem conexão com DaVinci)")
    print("   Os comentários serão exibidos aqui, mas não na timeline")
else:
    print("\n✅ Conectado ao DaVinci Resolve com sucesso!")

print("-" * 60)

def buscar_videos_do_projeto():
    """
    Busca todos os vídeos do projeto atual diretamente da API do Frame.io
    Não depende mais do histórico local
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    url = f"https://api.frame.io/v4/accounts/{ACCOUNT_ID}/folders/{FOLDER_ID}/files"
    
    print("📡 Buscando vídeos do projeto no Frame.io...")
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            videos = r.json().get("data", [])
            
            if not videos:
                print("📭 Nenhum vídeo encontrado no projeto.")
                return {"uploads": [], "ultimo": None}
            
            # Converte para o formato esperado pelo script
            uploads = []
            for v in videos:
                # Formata a data (yyyy-mm-dd)
                data = v.get("created_at", "")[:10]
                uploads.append({
                    "file_id": v["id"],
                    "nome": v["name"],
                    "data": data
                })
            
            # Ordena por data (mais recente primeiro)
            uploads.sort(key=lambda x: x["data"], reverse=True)
            
            print(f"✅ {len(uploads)} vídeo(s) encontrado(s)")
            return {"uploads": uploads, "ultimo": uploads[0]["file_id"] if uploads else None}
        else:
            print(f"❌ Erro ao buscar vídeos: {r.status_code}")
            return {"uploads": [], "ultimo": None}
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return {"uploads": [], "ultimo": None}

def escolher_video_ui(historico):
    """Interface gráfica para escolher o vídeo (agora com dados da API)"""
    if not historico["uploads"]:
        print("📭 Nenhum vídeo encontrado no projeto.")
        return None

    uploads = historico["uploads"]

    root = Tk()
    root.title("Selecione o vídeo")
    root.geometry("600x400")

    scrollbar = Scrollbar(root)
    scrollbar.pack(side="right", fill="y")

    listbox = Listbox(root, yscrollcommand=scrollbar.set)
    for up in uploads:
        nome = up['nome']
        data = up['data']
        listbox.insert(END, f"{nome} - {data}")
    listbox.pack(fill="both", expand=True, padx=10, pady=10)
    scrollbar.config(command=listbox.yview)

    # Seleciona o primeiro (mais recente) por padrão
    listbox.select_set(0)

    resultado = []

    def confirmar():
        selecao = listbox.curselection()
        if selecao:
            resultado.append(uploads[selecao[0]])
        root.quit()
        root.destroy()

    def cancelar():
        root.quit()
        root.destroy()

    btn_frame = Frame(root)
    btn_frame.pack(pady=5)
    Button(btn_frame, text="Selecionar", command=confirmar).pack(side="left", padx=5)
    Button(btn_frame, text="Cancelar", command=cancelar).pack(side="left", padx=5)

    root.mainloop()

    return resultado[0] if resultado else None

def buscar_comentarios(file_id):
    """Busca comentários no Frame.io"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    url = f"https://api.frame.io/v4/accounts/{ACCOUNT_ID}/files/{file_id}/comments"

    print(f"\n🔍 Buscando comentários...")

    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"❌ Erro na API: {r.status_code}")
            if r.status_code == 404:
                print("   Nenhum comentário encontrado para este vídeo")
            return []
        return r.json().get("data", [])
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return []

def exibir_comentarios_console(comentarios):
    """Exibe os comentários no console"""
    if not comentarios:
        print("\n📭 Nenhum comentário encontrado.")
        return

    print(f"\n📋 {len(comentarios)} comentário(s) encontrado(s):")
    print("-" * 60)
    for i, c in enumerate(comentarios, 1):
        frames = c['timestamp']
        segundos = frames / 24.0  # assume 24fps para exibição
        print(f"{i}. Frame {frames} ({segundos:.2f}s) - {c['text']}")
    print("-" * 60)

def adicionar_marcadores(comentarios, tl):
    """Adiciona marcadores na timeline usando timestamps em FRAMES"""
    if not comentarios:
        return

    try:
        if tl is None:
            print("❌ Timeline inválida")
            return

        fps = float(tl.GetSetting("timelineFrameRate"))
        frame_inicial = int(tl.GetStartFrame())
        frame_final = int(tl.GetEndFrame())
        duracao_frames = frame_final - frame_inicial

        print(f"\n   Frame rate: {fps} fps")
        print(f"   Frame inicial: {frame_inicial}")
        print(f"   Frame final: {frame_final}")
        print(f"   Duração do vídeo: {duracao_frames} frames")

        adicionados = 0
        falhas = 0

        for i, comment in enumerate(comentarios, 1):
            try:
                # O timestamp da API V4 está em FRAMES!
                timestamp_frames = comment.get('timestamp', 0)
                texto = comment.get('text', 'Sem texto')

                # O timestamp já é o frame desejado
                frame_relativo = timestamp_frames

                # Verifica se está dentro da duração
                if frame_relativo < 0:
                    frame_relativo = 0
                    print(f"      Frame ajustado para início")
                elif frame_relativo >= duracao_frames:
                    print(f"   ⚠️ Comentário {i}: frame {timestamp_frames} além da duração")
                    print(f"      Colocando no último frame")
                    frame_relativo = duracao_frames - 1

                # Frame absoluto (para referência)
                frame_absoluto = frame_inicial + frame_relativo

                # Define cor baseada no texto
                texto_lower = texto.lower()
                if any(p in texto_lower for p in ['aprov', 'ok', '👍', '✅', 'nice']):
                    cor = "Green"
                elif any(p in texto_lower for p in ['ajust', 'corrig', 'erro', 'fix', 'problema']):
                    cor = "Red"
                else:
                    cor = "Yellow"

                # Nome fixo sem espaços para o marcador
                nome_marcador = "FrameioComment"
                resultado = tl.AddMarker(frame_relativo, cor, nome_marcador, texto, 1, "")

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
        print(f"❌ Erro: {e}")
        exibir_comentarios_console(comentarios)

# ============ EXECUÇÃO PRINCIPAL ============

# 1. Busca vídeos do projeto ATUAL via API (não usa histórico local)
videos_projeto = buscar_videos_do_projeto()

# 2. Escolhe o vídeo na interface
video = escolher_video_ui(videos_projeto)

if not video:
    print("❌ Nenhum vídeo selecionado")
    sys.exit()

print(f"\n🎥 Vídeo: {video['nome']}")
print(f"📌 File ID: {video['file_id']}")

# 3. Busca comentários do vídeo selecionado
comentarios = buscar_comentarios(video['file_id'])

# 4. Adiciona na timeline ou exibe no console
if comentarios:
    if not modo_console and timeline:
        adicionar_marcadores(comentarios, timeline)
    else:
        exibir_comentarios_console(comentarios)
else:
    print("\n📭 Nenhum comentário encontrado.")

print("\n✅ Script finalizado!")