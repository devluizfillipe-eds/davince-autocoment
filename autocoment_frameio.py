import requests
import json
import DaVinciResolveScript as dvr

# ==============================
# CONFIG
# ==============================

CLIENT_ID = "SEU_CLIENT_ID"
CLIENT_SECRET = "SEU_CLIENT_SECRET"
REFRESH_TOKEN = "SEU_REFRESH_TOKEN"

PARENT_ASSET_ID = "SEU_PARENT_ASSET_ID"

FRAMEIO_API = "https://api.frame.io"

# ==============================

def get_access_token():
    url = "https://api.frame.io/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN
    }

    r = requests.post(url, json=payload)
    return r.json()["access_token"]


def upload_video(file_path, token):

    import os

    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)

    url = f"{FRAMEIO_API}/v2/assets/{PARENT_ASSET_ID}/children"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "name": filename,
        "type": "file",
        "filetype": "video/mp4",
        "filesize": filesize
    }

    r = requests.post(url, headers=headers, json=payload)

    data = r.json()

    upload_url = data["upload_urls"][0]
    asset_id = data["id"]

    with open(file_path, "rb") as f:

        requests.put(
            upload_url,
            data=f,
            headers={
                "Content-Type": "video/mp4",
                "x-amz-acl": "private"
            }
        )

    return asset_id


def get_comments(asset_id, token):

    url = f"{FRAMEIO_API}/v2/assets/{asset_id}/comments"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(url, headers=headers)

    return r.json()


def create_markers(comments):

    resolve = dvr.scriptapp("Resolve")
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()

    fps = float(timeline.GetSetting("timelineFrameRate"))

    for c in comments:

        sec = c["timestamp"]
        text = c["text"]

        frame = int(sec * fps)

        timeline.AddMarker(
            frame,
            "Red",
            "Frame.io",
            text,
            1
        )


def sync():

    resolve = dvr.scriptapp("Resolve")

    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()

    video_name = timeline.GetName() + ".mp4"

    token = get_access_token()

    url = f"{FRAMEIO_API}/v2/assets"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(url, headers=headers)

    assets = r.json()

    asset_id = None

    for a in assets:

        if a["name"] == video_name:
            asset_id = a["id"]

    if asset_id is None:
        print("Video não encontrado no Frame.io")
        return

    comments = get_comments(asset_id, token)

    create_markers(comments)


if __name__ == "__main__":
    sync()