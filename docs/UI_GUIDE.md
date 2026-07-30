# UI guide

Open **http://HOST:8000/** (root URL — no `/ui`).

## Layout

1. **Top** — App name, theme (System / Light / Dark), link to API docs  
2. **Status** — AVR reachable or not  
3. **Tabs** — Setup Menu | Info  
4. **Left** — Sections (Audio, Video, Inputs, Speakers, Network, General)  
5. **Middle** — Items in that section  
6. **Right** — Live controls for the selected page  

## How changes apply

- Most radios/selects apply **live** to the AVR (like Denon’s web UI).  
- Some pages need an explicit **Set** button (Audio Delay, LFE, Power On Level custom value, Source Level, …).  
- **Network Settings** never auto-save — use Save / Connect and read the warning.  

## Greyed (“inactive”) items

Denon greys menu entries when the current input / amp assign / signal does not allow them (e.g. Restorer, Dialog Level, ZONE2).  
This UI mirrors that. Hover for the reason.

## Setup Lock

**General → Setup Lock**:

- **On** — other Setup items grey out; clicks redirect here; API writes to other pages return 403.  
- **Off** — normal editing resumes.  

## Edit modes (dev build)

Top bar **Realtime | Save** toggle (also in Settings → Edit mode):

- **Realtime** — changes apply to the AVR as you edit (original behavior).
- **Save** — edit locally, then press **Save / Set**. Soft-refresh pauses while dirty or focused so typing is not wiped.

Network pages always require explicit Save. Manual EQ still uses **Set**.

Menu grey-outs continue to refresh on their own poll (~15s), independent of edit mode.

See [DEV.md](DEV.md) for the `:dev` Docker image.

Special UI for 9-band Graphic EQ (when MultEQ is Off). Channel / Speaker
Selection lists come from the AVR (Amp Assign aware — not hard-coded).

Uses `/api/endpoints/audio_graphiceq_s_audio` for live edits, plus:

| API | Purpose |
|-----|---------|
| `GET /api/manual-eq/export` | All live channel curves + Amp Assign fingerprint |
| `POST /api/manual-eq/import` | Restore curves; **blocked** if Amp Assign differs; missing speakers skipped with warnings |

Export / Import buttons are on the Manual EQ page.

## Themes

Theme preference is stored in the browser (`localStorage`). It does not affect the AVR.
