import json
import requests
import DaVinciResolveScript as dvr
import sys

# ================= CONFIG =================

FRAMEIO_TOKEN = "COLE_SEU_TOKEN_AQUI"  # Só edita uma vez
FPS = 29.97  # Ajuste conforme seu projeto

# ========================================

def seconds_to_frames(seconds):
    return int(seconds * FPS)

def get_comments(asset_id):
    url = f"https://api.frame.io/v4/assets/{asset_id}/comments"
    headers = {
        "Authorization": f"Bearer {FRAMEIO_TOKEN}"
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def main():
    # Verificar se o Asset ID foi passado
    if len(sys.argv) < 2:
        print("❌ Erro: Informe o ASSET_ID")
        print("Uso: python3 frameio_comments.py SEU_ASSET_ID_AQUI")
        return

    asset_id = sys.argv[1]
    print(f"🎬 Asset ID: {asset_id}")

    # Connect to Resolve
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        print("❌ Erro: Conectando ao DaVinci Resolve")
        return

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    timeline = project.GetCurrentTimeline()

    if not timeline:
        print("❌ Nenhuma timeline ativa.")
        return

    # Remove all markers
    markers = timeline.GetMarkers()
    for frame in markers.keys():
        timeline.DeleteMarkerAtFrame(frame)

    print("🧹 Markers antigos apagados.")

    # Fetch Frame.io comments
    try:
        comments = get_comments(asset_id)
    except Exception as e:
        print(f"❌ Erro ao buscar comentários: {e}")
        return

    for c in comments:
        ts = c.get("timestamp", 0)
        text = c.get("body", "")
        author = c.get("user", {}).get("name", "Frame.io")

        frame = seconds_to_frames(ts)

        marker_text = f"{author}: {text}"

        timeline.AddMarker(
            frame,
            "Blue",
            marker_text,
            "",
            1
        )

    print(f"✅ {len(comments)} markers importados.")

if __name__ == "__main__":
    main()