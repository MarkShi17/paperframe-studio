# Paperframe

A research video player. Import an arXiv paper, watch a narrated diagram, and pause to generate a follow-up video about that scene. Return to the parent video at the same timestamp. The included Transformer walkthrough plays immediately.

## Run on Replit

1. Import the project ZIP at https://replit.com/import and choose **Run**.
2. Add **ELEVENLABS_API_KEY** in Replit Secrets for ElevenLabs narration. Optionally set **ELEVENLABS_VOICE_ID**. New renders pick up the voice setting. Import 1706.03762 to regenerate the bundled walkthrough with ElevenLabs.
3. For synthesized explanations on Replit, enable its OpenAI integration (AI_INTEGRATIONS_OPENAI_BASE_URL and AI_INTEGRATIONS_OPENAI_API_KEY), or add OPENAI_API_KEY in Secrets. The default model is gpt-4o-mini. PAPERFRAME_MODEL overrides it.

The server fetches arXiv metadata and accessible HTML sections. When HTML is unavailable, the player labels the result an abstract walkthrough. Without a language model, Paperframe builds an extractive walkthrough and uses matched source passages or prepared explanations for follow-ups. Linux defaults to eSpeak when ElevenLabs is unconfigured. The bundled film uses macOS speech.

## Local macOS

Install FFmpeg and the packages in requirements.txt. Run `python app.py`, then open http://127.0.0.1:8765. Optional local credentials go in .env. On macOS 26 with Apple Intelligence enabled, `mkdir -p .build && swiftc -parse-as-library Narrator.swift -o .build/narrator` enables the on-device script writer.

Generated MP4s, diagrams and source excerpts are stored in public/media. The server is intended for a hackathon workspace preview. Anyone with access to the running instance can request renders using its configured providers.
