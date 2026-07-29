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

## Manual EQ

Special UI for 9-band Graphic EQ (when MultEQ is Off). Uses dedicated API helpers under `/api/audio/manual-eq*`.

## Themes

Theme preference is stored in the browser (`localStorage`). It does not affect the AVR.
