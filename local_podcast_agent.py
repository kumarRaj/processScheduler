#!/usr/bin/env python3
"""Create a local Open Podcast episode from a document without UI prompts.

The agent deliberately uses the local configuration established for this machine:
LM Studio for writing, Kokoro for speech, and Open Podcast's ``tech_discussion``
and ``tech_experts`` profiles.  It never sends the source document to a cloud API.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


DEFAULT_OPEN_PODCAST_DIR = Path(__file__).resolve().parents[1] / "open-podcast"
DEFAULT_KOKORO_NATIVE_DIR = Path(__file__).resolve().parents[1] / "kokoro-fastapi"
ROOT = DEFAULT_OPEN_PODCAST_DIR
API = "http://127.0.0.1:5055/api"
NATIVE_KOKORO_URL = "http://127.0.0.1:8881/v1/models"
POLL_SECONDS = 15


class AgentError(RuntimeError):
    pass


def say(message: str) -> None:
    print(f"[local-podcast] {message}", flush=True)


def request(method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> dict | bytes:
    headers = {"Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(f"{API}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            data = response.read()
            if response.headers.get_content_type() == "application/json":
                return json.loads(data)
            return data
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise AgentError(f"{method} {path} failed ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise AgentError(f"Cannot reach Open Podcast at {API}: {error.reason}") from error


def multipart(fields: dict[str, str], file_field: str, source: Path) -> tuple[bytes, str]:
    boundary = f"----localpodcast{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend((
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
            value.encode(), b"\r\n",
        ))
    chunks.extend((
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{source.name}"\r\n'.encode(),
        b"Content-Type: application/octet-stream\r\n\r\n",
        source.read_bytes(), b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    say("Running: " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def native_kokoro_is_ready() -> bool:
    try:
        with urllib.request.urlopen(NATIVE_KOKORO_URL, timeout=3) as response:
            return response.status == 200
    except urllib.error.URLError:
        return False


def start_native_kokoro(kokoro_dir: Path) -> subprocess.Popen[bytes] | None:
    """Start native Kokoro for this run, returning only a process we own."""
    if native_kokoro_is_ready():
        say("Using the already-running native Kokoro TTS service.")
        return None

    executable = kokoro_dir / ".venv" / "bin" / "uvicorn"
    if not executable.is_file():
        raise AgentError(
            f"Native Kokoro is not installed at {kokoro_dir}. "
            "Pass --kokoro-native-dir or complete the one-time native Kokoro setup."
        )
    environment = os.environ | {
        "USE_GPU": "true",
        "DEVICE_TYPE": "mps",
        "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        "PYTHONPATH": f"{kokoro_dir}:{kokoro_dir / 'api'}",
        "MODEL_DIR": "src/models",
        "VOICES_DIR": "src/voices/v1_0",
        "WEB_PLAYER_PATH": str(kokoro_dir / "web"),
    }
    say("Starting native Apple Silicon Kokoro TTS for this generation.")
    process = subprocess.Popen(
        [str(executable), "api.src.main:app", "--host", "0.0.0.0", "--port", "8881"],
        cwd=kokoro_dir,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(24):
        if native_kokoro_is_ready():
            return process
        if process.poll() is not None:
            raise AgentError("Native Kokoro exited while starting. Check its local installation.")
        time.sleep(5)
    process.terminate()
    raise AgentError("Native Kokoro did not become ready within two minutes.")


def stop_native_kokoro(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    say("Stopping native Kokoro TTS started for this generation.")
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()


def ensure_services(kokoro_dir: Path) -> subprocess.Popen[bytes] | None:
    """Start Open Podcast and a native TTS service for this generation."""
    try:
        subprocess.run(["colima", "status"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        run(["colima", "start", "--cpu", "6", "--memory", "8"])
    run(["docker", "compose", "up", "-d"], cwd=ROOT)
    return start_native_kokoro(kokoro_dir)


def wait_for_api() -> None:
    for _ in range(40):
        try:
            request("GET", "/episode-profiles")
            return
        except AgentError:
            time.sleep(3)
    raise AgentError("Open Podcast did not become ready within two minutes.")


def require_profiles() -> None:
    """Test the exact models the selected profiles will use before spending time."""
    episodes = request("GET", "/episode-profiles")
    speakers = request("GET", "/speaker-profiles")
    episode = next((entry for entry in episodes if entry["name"] == "tech_discussion"), None)
    speaker = next((entry for entry in speakers if entry["name"] == "tech_experts"), None)
    if not episode:
        raise AgentError("The local 'tech_discussion' profile is missing. Run the one-time Open Podcast setup first.")
    if not speaker:
        raise AgentError("The local 'tech_experts' speaker profile is missing. Run the one-time Open Podcast setup first.")
    model_ids = {episode.get("outline_llm"), episode.get("transcript_llm"), speaker.get("voice_model")}
    if None in model_ids or "" in model_ids:
        raise AgentError("A selected profile has no model attached; refusing to start a generation that will fail.")
    for model_id in sorted(model_ids):
        assert isinstance(model_id, str)
        say(f"Testing configured local model: {model_id}")
        result = request("POST", f"/models/{model_id}/test", b"{}", "application/json")
        if not result.get("success"):
            raise AgentError(f"Configured model {model_id} did not pass its health check: {result.get('message')}")


def safe_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in name).strip("_") or "podcast"


def main() -> int:
    global ROOT
    parser = argparse.ArgumentParser(description="Autonomously make a local podcast from a PDF or text document.")
    parser.add_argument("source", type=Path, help="PDF, TXT, Markdown, CSV, or JSON source document")
    parser.add_argument("--title", help="Episode title (defaults to the source filename)")
    parser.add_argument("--output-dir", type=Path, default=Path.home() / "Downloads",
                        help="Where finished MP3s are written (default: ~/Downloads)")
    parser.add_argument("--no-start-services", action="store_true",
                        help="Fail if the local stack is not already running")
    parser.add_argument("--open-podcast-dir", type=Path, default=DEFAULT_OPEN_PODCAST_DIR,
                        help="Open Podcast checkout (default: ../open-podcast next to this repository)")
    parser.add_argument("--kokoro-native-dir", type=Path, default=DEFAULT_KOKORO_NATIVE_DIR,
                        help="Native Kokoro checkout (default: ../kokoro-fastapi next to this repository)")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.is_file():
        raise AgentError(f"Source file does not exist: {source}")
    ROOT = args.open_podcast_dir.expanduser().resolve()
    kokoro_dir = args.kokoro_native_dir.expanduser().resolve()
    if not (ROOT / "docker-compose.yml").is_file():
        raise AgentError(
            f"Open Podcast checkout not found at {ROOT}. "
            "Pass --open-podcast-dir /path/to/open-podcast."
        )
    title = args.title or source.stem
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    native_kokoro_process = None
    try:
        if not args.no_start_services:
            native_kokoro_process = ensure_services(kokoro_dir)
        wait_for_api()
        require_profiles()

        say("Creating a notebook and importing the document into Open Podcast.")
        notebook = request("POST", "/notebooks", json.dumps({
        "name": title, "description": f"Autonomous local podcast source: {source.name}"
        }).encode(), "application/json")
        notebook_id = notebook["id"]
        payload, content_type = multipart({
        "type": "upload", "notebooks": json.dumps([notebook_id]), "title": title,
        "embed": "false", "async_processing": "false", "delete_source": "false",
        }, "file", source)
        imported = request("POST", "/sources", payload, content_type)
        if not imported.get("id") or not (imported.get("full_text") or "").strip():
            raise AgentError("Document import returned no extracted text; refusing to generate an empty episode.")
        say(f"Validated source extraction ({len(imported['full_text'])} characters).")

        briefing = (
        "Use the supplied document as the sole factual source. Do not claim personal "
        "production experience or invent examples, statistics, or citations. Explain "
        "requirements, architecture, bottlenecks, and trade-offs in plain, rigorous language."
        )
        say("Writing the discussion and rendering local voice clips. This can take several minutes.")
        job = request("POST", "/podcasts/generate", json.dumps({
        "episode_profile": "tech_discussion", "speaker_profile": "tech_experts",
        "episode_name": title, "notebook_id": notebook_id, "briefing_suffix": briefing,
        }).encode(), "application/json")
        job_id = job["job_id"]

        while True:
            status = request("GET", f"/podcasts/jobs/{job_id}")
            state = status.get("status", "unknown")
            say(f"Generation status: {state}")
            if state == "completed":
                result = status.get("result") or {}
                episode_id = result.get("episode_id")
                if not episode_id:
                    raise AgentError("The generation completed but did not return an episode ID.")
                break
            if state in {"failed", "error", "cancelled"}:
                raise AgentError(status.get("error_message") or f"Generation ended with status {state}.")
            time.sleep(POLL_SECONDS)

        base = safe_name(title)
        mp3 = output_dir / f"{base}.mp3"
        spotify = output_dir / f"{base}_spotify.mp3"
        say(f"Downloading completed audio to {mp3}")
        audio = request("GET", f"/podcasts/episodes/{episode_id}/audio")
        assert isinstance(audio, bytes)
        if len(audio) < 1_024:
            raise AgentError("Completed episode returned an unexpectedly small audio file.")
        mp3.write_bytes(audio)
        say("Validating the downloaded MP3.")
        run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
             "-of", "default=noprint_wrappers=1", str(mp3)])
        run(["ffmpeg", "-y", "-i", str(mp3), "-map_metadata", "-1", "-codec:a", "libmp3lame",
             "-b:a", "128k", "-ar", "44100", "-ac", "2", "-write_xing", "0", str(spotify)])
        say("Validating the Spotify-ready MP3.")
        run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,bit_rate,sample_rate,channels",
             "-of", "default=noprint_wrappers=1", str(spotify)])
        say(f"Finished. Standard MP3: {mp3}")
        say(f"Spotify-ready MP3: {spotify}")
        return 0
    finally:
        stop_native_kokoro(native_kokoro_process)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AgentError, subprocess.CalledProcessError) as error:
        print(f"[local-podcast] ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
