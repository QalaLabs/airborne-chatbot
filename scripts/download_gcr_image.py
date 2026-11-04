import os
import sys
import gzip
import json
import tarfile
import subprocess
import urllib.request
from pathlib import Path

DEST_DIR = Path("downloads/gcr_build")
DEST_DIR.mkdir(parents=True, exist_ok=True)

HOST = "asia-south1-docker.pkg.dev"
REPO = "airborne-aviation-505100/cloud-run-source-deploy/airborne-chatbot"
IMAGE_TAG = "latest"

def get_token():
    print("[1/5] Fetching Google Cloud authentication token...", flush=True)
    token = subprocess.check_output("gcloud auth print-access-token", shell=True).decode().strip()
    return token

def download_file(url, token, dest_path, expected_size=None):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/octet-stream"
    })
    
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out:
        total = int(resp.headers.get("content-length", 0)) or expected_size or 0
        downloaded = 0
        chunk_size = 1024 * 512
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total > 0 and downloaded % (1024 * 1024 * 5) < chunk_size:
                pct = (downloaded / total) * 100
                print(f"      Downloaded {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB ({pct:.1f}%)", flush=True)

def main():
    token = get_token()
    
    print("[2/5] Fetching Docker image manifest...", flush=True)
    manifest_url = f"https://{HOST}/v2/{REPO}/manifests/{IMAGE_TAG}"
    req = urllib.request.Request(manifest_url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json"
    })
    
    with urllib.request.urlopen(req) as resp:
        manifest_data = json.loads(resp.read().decode())
    
    manifest_file = DEST_DIR / "image-manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"      Saved manifest to {manifest_file}", flush=True)

    config_digest = manifest_data["config"]["digest"]
    config_hash = config_digest.split(":")[-1]
    config_file = DEST_DIR / f"{config_hash}.json"
    
    print(f"[3/5] Downloading image config ({config_digest[:20]}...)...", flush=True)
    config_url = f"https://{HOST}/v2/{REPO}/blobs/{config_digest}"
    download_file(config_url, token, config_file)
    print(f"      Saved image config to {config_file}", flush=True)

    layers_dir = DEST_DIR / "layers"
    layers_dir.mkdir(exist_ok=True)
    
    layers = manifest_data.get("layers", [])
    print(f"[4/5] Downloading all {len(layers)} image layers (total ~213 MB)...", flush=True)
    
    tar_layers = []
    
    for idx, layer in enumerate(layers):
        digest = layer["digest"]
        layer_hash = digest.split(":")[-1]
        size_mb = layer.get("size", 0) / (1024 * 1024)
        gz_layer_file = layers_dir / f"{layer_hash}.tar.gz"
        tar_layer_name = f"{layer_hash}/layer.tar"
        unpacked_layer_dir = layers_dir / layer_hash
        unpacked_layer_dir.mkdir(exist_ok=True)
        unpacked_layer_file = unpacked_layer_dir / "layer.tar"
        
        print(f"\n   -> Layer {idx+1}/{len(layers)}: {size_mb:.2f} MB ({digest[:19]}...)", flush=True)
        
        if not unpacked_layer_file.exists():
            layer_url = f"https://{HOST}/v2/{REPO}/blobs/{digest}"
            download_file(layer_url, token, gz_layer_file, expected_size=layer.get("size"))
            
            # Decompress gzip blob into layer.tar
            print(f"      Decompressing layer to {unpacked_layer_file.name}...", flush=True)
            with gzip.open(gz_layer_file, "rb") as f_in, open(unpacked_layer_file, "wb") as f_out:
                while True:
                    buf = f_in.read(1024 * 512)
                    if not buf:
                        break
                    f_out.write(buf)
            
            # Remove intermediate gz file to save disk space
            if gz_layer_file.exists():
                gz_layer_file.unlink()
        else:
            print("      Already downloaded and extracted.", flush=True)
            
        tar_layers.append(tar_layer_name)

    print("\n[5/5] Packaging complete Docker-loadable image tarball...", flush=True)
    docker_manifest = [
        {
            "Config": f"{config_hash}.json",
            "RepoTags": [
                f"{HOST}/{REPO}:{IMAGE_TAG}",
                "airborne-chatbot:latest"
            ],
            "Layers": [f"layers/{tl}" for tl in tar_layers]
        }
    ]
    
    docker_manifest_file = DEST_DIR / "manifest.json"
    with open(docker_manifest_file, "w", encoding="utf-8") as f:
        json.dump(docker_manifest, f, indent=2)

    image_tar_path = DEST_DIR / "airborne-chatbot-docker-image.tar"
    print(f"      Writing {image_tar_path}...", flush=True)
    with tarfile.open(image_tar_path, "w") as tar:
        tar.add(docker_manifest_file, arcname="manifest.json")
        tar.add(config_file, arcname=f"{config_hash}.json")
        for tl in tar_layers:
            layer_path = layers_dir / tl
            tar.add(layer_path, arcname=f"layers/{tl}")

    print("\n" + "=" * 70, flush=True)
    print("✅ Complete GCR/Artifact Registry Image Downloaded Successfully!", flush=True)
    print(f"📍 Docker Image Archive : {image_tar_path} ({image_tar_path.stat().st_size / (1024*1024):.1f} MB)", flush=True)
    print(f"📍 Cloud Build Source   : {DEST_DIR / 'airborne-chatbot-cloudbuild-source.zip'}", flush=True)
    print(f"📍 Cloud Build Log      : {DEST_DIR / 'build-log.txt'}", flush=True)
    print(f"📍 Cloud Build Metadata : {DEST_DIR / 'build-metadata.json'}", flush=True)
    print(f"💡 To load and run locally: docker load -i \"{image_tar_path}\"", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
