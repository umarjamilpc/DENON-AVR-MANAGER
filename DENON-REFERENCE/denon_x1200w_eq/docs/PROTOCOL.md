# Denon AVR-X1200W Manual EQ — reverse-engineered web protocol

Verified live against `http://192.168.20.50` (GoAhead-Webs) on 2026-07-29.

## Discovery summary

| Layer | Per-band Manual EQ? |
|-------|---------------------|
| Telnet `:23` | **No** — only `PSGEQ ON/OFF` |
| SETUP web UI `:80` | **Yes** — HTML form POST to `s_audio.asp` |

Manual EQ is labeled **Graphic EQ** in paths (`GRAPHICEQ`) and **Manual EQ** in the UI.

## Pages

| Purpose | URL |
|---------|-----|
| Setup home | `/SETUP/f_home.asp` |
| Audio menu | `/SETUP/AUDIO/f_audio.asp` → right frame lists Manual EQ |
| Manual EQ frameset | `/SETUP/AUDIO/GRAPHICEQ/f_audio.asp` |
| Manual EQ form (read) | `GET /SETUP/AUDIO/GRAPHICEQ/d_audio.asp` |
| Manual EQ submit (write) | `POST /SETUP/AUDIO/GRAPHICEQ/s_audio.asp` |
| Hidden reply frame | `/SETUP/dummy.asp` (`target=audio2`) |

Form: `name=surrParaForm`, `method=POST`, `action=s_audio.asp`, `enctype=application/x-www-form-urlencoded`.

## Fields

### Always present

| Field | Values | Notes |
|-------|--------|-------|
| `setPureDirectOn` | `ON` / `OFF` | Usually `OFF` |
| `setSetupLock` | `ON` / `OFF` | Usually `OFF` |
| `radioGraphicEQ` | `ON` / `OFF` | Master Manual EQ enable |
| `setGEQCurveCopy` | `off` or `Set` | Curve Copy button |
| `setGEQSetDefaults` | `off` or `Set` | Set Defaults button |

### Present when Manual EQ = ON

| Field | Values | Notes |
|-------|--------|-------|
| `listGEQSpSelection` | `ALL`, `LRS`, `EAC` | All / Left-Right / Each |
| `listGEQAdjustEQ` | see channels below | Speaker (or pair) being edited |
| `textGEQ63` … `textGEQ16k` | `-20.0` … `6.0` step `0.5` | Band gains in dB (string) |
| `setAdjustEQ` | `off` or `Set` | **Must be `Set` to apply bands** |

Band field names:

```
textGEQ63, textGEQ125, textGEQ250, textGEQ500,
textGEQ1k, textGEQ2k, textGEQ4k, textGEQ8k, textGEQ16k
```

### Channels (`listGEQAdjustEQ`) observed on this unit

With Speaker Selection = **Each** (`EAC`):

| Code | Label |
|------|-------|
| `FL` | Front L |
| `FR` | Front R |
| `CEN` | Center |
| `SL` | Surround L |
| `SR` | Surround R |
| `TML` | Top Middle L |
| `TMR` | Top Middle R |

Channel list can change with sound mode / speaker config. Always parse `<option>` tags from `d_audio.asp` rather than hard-coding alone.

### Constraints (receiver UI)

- MultEQ / Audyssey must be **Off** for Manual EQ bands to be editable.
- Not available in Direct / Pure Direct.
- Range: **-20.0 … +6.0 dB**, step **0.5**.

## Write operations

### Enable / disable Manual EQ

```http
POST /SETUP/AUDIO/GRAPHICEQ/s_audio.asp
Content-Type: application/x-www-form-urlencoded

setPureDirectOn=OFF&setSetupLock=OFF&radioGraphicEQ=ON&setGEQCurveCopy=off&setGEQSetDefaults=off
```

Use `radioGraphicEQ=OFF` to disable.

### Change speaker selection / channel (view)

Submit the form **without** `setAdjustEQ=Set` (leave `off`). `onchange=listBox()` does the same.

### Apply band curve (Set button)

```http
POST /SETUP/AUDIO/GRAPHICEQ/s_audio.asp
Content-Type: application/x-www-form-urlencoded

setPureDirectOn=OFF
&setSetupLock=OFF
&radioGraphicEQ=ON
&listGEQSpSelection=EAC
&listGEQAdjustEQ=FL
&textGEQ63=-2.5
&textGEQ125=-0.5
&textGEQ250=-1.0
&textGEQ500=-0.5
&textGEQ1k=0.0
&textGEQ2k=0.0
&textGEQ4k=-1.5
&textGEQ8k=-3.0
&textGEQ16k=-5.0
&setAdjustEQ=Set
&setGEQCurveCopy=off
&setGEQSetDefaults=off
```

**Rules observed**

1. Send **all nine** band fields together with `setAdjustEQ=Set`.
2. Do **not** send `setAdjustEQ=Set` when only switching channel/mode — that avoids accidental overwrites.
3. After write, re-`GET d_audio.asp` to verify.
4. Wait ~0.5–1.5 s after POST before re-read (UI does similar).

## Captured sample curves (this AVR)

Front L (`FL`), 2026-07-29:

| Band | dB |
|------|----|
| 63 | -2.5 |
| 125 | -0.5 |
| 250 | -1.0 |
| 500 | -0.5 |
| 1k | 0.0 |
| 2k | 0.0 |
| 4k | -1.5 |
| 8k | -3.0 |
| 16k | -5.0 |

Center (`CEN`) differed (not identical to FL), confirming per-channel storage.

HTML captures: `../captures/`.

## Session restore note

Probe session briefly set Manual EQ **ON** to read the band form, then restored **OFF**. Audyssey MultEQ / Dynamic EQ / Dynamic Volume were already Off and left Off.
