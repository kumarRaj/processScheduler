# Local Podcast Agent

Turn a local PDF, text, Markdown, CSV, or JSON file into a podcast using only local models. The agent is a command-line orchestrator for an existing Open Podcast checkout: it starts the local stack when needed, validates its dependencies, imports the source, waits for generation, verifies the finished audio, and creates a Spotify-compatible MP3.

It does not send source documents to a cloud LLM. The intended configuration is LM Studio for writing and Kokoro for speech.

## Requirements

- macOS with Python 3, Docker, Colima, and FFmpeg installed
- An Open Podcast checkout, either next to this repository in `../open-podcast` or supplied with `--open-podcast-dir`
- A native Kokoro FastAPI checkout, either next to this repository in `../kokoro-fastapi` or supplied with `--kokoro-native-dir`
- LM Studio running a local OpenAI-compatible model at port `1234`
- Open Podcast configured to reach LM Studio and a local Kokoro TTS service
- The Open Podcast profiles `tech_discussion` and `tech_experts`

The profile requirements are deliberate. `tech_discussion` must point its outline and transcript models at the local LM Studio model. `tech_experts` must point its voice model at local Kokoro. The agent health-checks these exact models before it imports a document or begins an expensive generation.

## One-time setup

1. Start LM Studio's local server and load the model you want to use for writing.
2. Configure Open Podcast with its local LM Studio credential/model and local Kokoro credential/model.
3. Configure `tech_discussion` and `tech_experts` to use those models.
4. Install the native Apple Silicon Kokoro environment and model once. The agent uses its OpenAI-compatible endpoint on port `8881`.

The agent starts Colima and `docker compose` when they are stopped. It starts native Kokoro only for the generation, waits for its health check, and stops only the process it started once the episode and Spotify copy have been validated. It does not create, store, or publish API keys.

## Generate a podcast

From this repository:

```bash
python3 local_podcast_agent.py "/path/to/document.pdf" \
  --open-podcast-dir "/path/to/open-podcast"
```

If both repositories are siblings, the `--open-podcast-dir` option is unnecessary:

```text
parent-folder/
├── local-podcast-agent/
└── open-podcast/
```

```bash
cd parent-folder/local-podcast-agent
python3 local_podcast_agent.py "/path/to/document.pdf"
```

Useful options:

```bash
# Give the episode a clear name
python3 local_podcast_agent.py report.pdf --title "Architecture review"

# Choose where the two MP3 files are written
python3 local_podcast_agent.py report.pdf --output-dir "/path/to/output"

# Require the local services to already be running
python3 local_podcast_agent.py report.pdf --no-start-services

# Use a Kokoro checkout outside the sibling-folder layout
python3 local_podcast_agent.py report.pdf --kokoro-native-dir "/path/to/kokoro-fastapi"
```

By default, files are written to the current user's Downloads folder:

- `<title>.mp3` — the Open Podcast episode
- `<title>_spotify.mp3` — metadata-free MP3, 128 kbps, 44.1 kHz stereo

Using the same title again replaces those two output files.

## What the agent validates

Before generation it checks that Open Podcast is reachable and that the selected writing and TTS models respond. It then verifies that the uploaded document produced extracted text. After generation it checks for a completed job, refuses unexpectedly small audio downloads, validates the MP3 with `ffprobe`, converts it with FFmpeg, and validates the converted file's codec, bitrate, sample rate, and stereo channels.

If any check fails, it exits with the relevant local error instead of silently producing an incomplete episode. Generation can take 10–20 minutes, depending on document size, local model speed, and available CPU.

## Privacy

The document, transcript, and audio stay on the machine when LM Studio and Kokoro are configured locally. Docker may download container images when they are not already available; that is separate from the content-generation path.
