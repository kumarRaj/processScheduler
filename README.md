# Local Podcast Agent

`local_podcast_agent.py` automates the workflow we just used. It makes no cloud-model calls. Its settled defaults are LM Studio for the script, Kokoro for voices, Open Podcast's `tech_discussion` format, and a Spotify-ready 128 kbps MP3.

Run it with a local document:

```bash
cd /path/to/local-podcast-agent
python3 local_podcast_agent.py "/path/to/document.pdf"
```

It starts Colima (with 8 GB if it is stopped), Open Podcast, and Kokoro as needed; verifies the exact local writing and TTS models selected by the profiles; creates a source notebook; imports and confirms extracted text; generates and monitors the episode; validates the downloaded MP3; transcodes it; validates that Spotify version; and writes two files to `~/Downloads`:

- `<document>.mp3` — the Open Podcast download
- `<document>_spotify.mp3` — metadata-free, 128 kbps, 44.1 kHz stereo MP3

The one-time local configuration must already exist in Open Podcast: the `tech_discussion` episode profile, `tech_experts` speaker profile, LM Studio credential/model, and Kokoro credential/model. The agent checks those conditions up front and fails clearly if they have been removed.

It does not ask routine questions or wait for manual status checks. It chooses the established local stack and validates each expensive boundary before moving on. It stops only when a local dependency or generation job has genuinely failed, preserving the API's error message for diagnosis.

Useful options:

```bash
python3 local_podcast_agent.py report.pdf --title "Architecture review"
python3 local_podcast_agent.py report.pdf --output-dir ~/Desktop
python3 local_podcast_agent.py report.pdf --no-start-services
```
