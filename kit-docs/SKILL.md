---
name: dagar-ink-shorts
description: Make a DAGAR CLIPS ink-style vertical short (round-head ink toons with mocap acting in real 3D Blender worlds, rendered on GitHub Actions, free TTS voiceover). Use for any new DAGAR ink video.
---

# DAGAR CLIPS ink shorts

## What you need
- The kit: `dagar-ink-kit.zip` (or the repo `chintudagar541-stack/wanderly`, branch `claude/dagar-blender`, folder `kits/dagar-ink/code`).
- A GitHub repo you can push to, so you can render on GitHub Actions.
- Read `README.md` and `CHARACTERS.md` from the kit first.

## Rules
- The story and its characters are always original. Reuse the saved cast presets from CHARACTERS.md (Jack, Sheriff, Ezra, Mortimer, Father Joe, Walt, Mayor, Doctor, cops, crowd…) or create new presets in the same style.
- Reply to the user in Hinglish. Use English for the video unless told otherwise.
- No captions and no logo unless the user asks.
- Background music and SFX stay at **20–30 % of the narrator's level** (about −12 dB gated RMS).
- Use free tools only (Blender bpy, Poly Haven CC0, CMU mocap, Kokoro/Piper TTS). No paid APIs, and never use Higgsfield.
- Report progress honestly and never claim a render succeeded before you have checked it.

## Pipeline
1. **Ideas → script.** Offer 10 ideas, then write the script the user picks (narration only, with paragraph breaks).
2. **Voiceover.** Write `audio/voiceover/<p>/lines.json` (narrator `kokoro:am_michael`, `gap` .5) and run the `TTS voices` workflow. For character voices, audition several Kokoro voices and pick by `asr_check.py` intelligibility plus fit.
3. **Timing.** Find the pauses with `ffmpeg -af silencedetect=n=-40dB:d=0.18`, map the phrases to the speech segments, then write `blender/<p>/shots.json` with cuts about 0.15 s before each phrase.
4. **Set.** Reuse `town.py` (western), `undertaker/sets.py` (graveyard, coffins, shop) or `zombie/city.py` (modern city), or write a new `sets.py` from primitives with Poly Haven textures.
5. **Shots.** In `story.py`, write one `s_<id>(sh)` per shot:
   - `stage()`, then `toon(sh, cid, preset)`
   - `stand` / `walk` acts with CMU clips
   - `override()` for hand targets
   - `hold()` props on `ch.hands[side]`
   - `cam_keys()` glides or `cu()` close-ups
   - `sh.keylight()`
6. **Stills review.** Push `job.json` in stills mode, fetch `previews/<p>`, build a contact sheet, and launch a reviewer agent acting as a strict director/cinematographer (readability, full backgrounds, 9:16 composition, glitches). Fix and re-render the changed shots until it says APPROVED.
7. **Final.** Set `job.json` to video mode at 1080×1920 (samples 12, chunk 10, `FAST`/`ADAPT` env). The join job runs `compose.py`. Fetch `final_share.mp4`, verify the length, loudness and frames, then send it.

## Gotchas
- `yaw 0` faces −Y.
- The `handR` pose key drives `ch.hands['R']`.
- Coffin/object `matrix_world` is stale right after creation.
- Add story characters to `sh.protect`.
- Text planes face −Y.
- Use the force-cancel REST call to stop runs.
- Artifact downloads are blocked locally, so always compose on CI.
