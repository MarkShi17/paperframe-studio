# Paperframe

A research video player. Import an arXiv paper, watch a narrated diagram, and pause to generate a follow-up video about that scene. Return to the parent video at the same timestamp. The included Transformer paper opens with a two-minute overview. Switch to the technical deep dive for tensor shapes, scaling, a worked softmax example, masking, and complexity. Both films play immediately.

## Run on Replit

1. Open [the Paperframe Replit workspace](https://replit.com/@markshi3/paperframe-studio) and choose **Run**. For a new workspace, import the GitHub repo or the project ZIP at https://replit.com/import.
2. Add **ELEVENLABS_API_KEY** in Replit Secrets for ElevenLabs narration. Optionally set **ELEVENLABS_VOICE_ID**. New renders use the key immediately. Choose **Use ElevenLabs voice** below a local-voice overview or deep dive to generate the same film with sponsor narration.
3. For synthesized explanations on Replit, enable its OpenAI integration (AI_INTEGRATIONS_OPENAI_BASE_URL and AI_INTEGRATIONS_OPENAI_API_KEY), or add OPENAI_API_KEY in Secrets. The default model is gpt-4o-mini. PAPERFRAME_MODEL overrides it.

The server reads arXiv HTML sections and original figure captions. If an HTML edition is unavailable, it extracts text from up to 20 PDF pages with page-level references. Scans without readable text fall back to a labeled abstract walkthrough. Without a configured script model, Paperframe builds a cited extractive walkthrough and uses matched source passages or prepared explanations for follow-ups. Linux defaults to eSpeak when ElevenLabs is unconfigured. The bundled film uses macOS speech.

## Overview and technical depth

The overview targets two minutes at a natural speaking pace. When the source has too little material, the app shows the shorter actual runtime. Technical tracks follow the available evidence and have no time target. For imported papers, the deep dive uses cited technical passages and renders supported numbered equations directly from arXiv’s TeX. With a script model configured it explains the equations and methods. Without one it reads the supporting passages. Paper sources shows the original equation and its link. PDF-only papers cite the corresponding pages. An abstract alone cannot support a technical track.

## Local macOS

Install FFmpeg and the packages in requirements.txt. Run `python app.py`, then open http://127.0.0.1:8765. Optional local credentials go in .env. Set PAPERFRAME_CLAUDE=1 to use an already authenticated Claude CLI for narration scripts. The app runs it without tools or MCP servers. Model-generated scenes must select supporting passages from the paper.

Generated MP4s, diagrams and source excerpts are stored in public/media. The server is intended for a hackathon workspace preview. Anyone with access to the running instance can request renders using its configured providers.
