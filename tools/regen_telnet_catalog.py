"""Regenerate telnet_commands.json with grouped controls + multi-model support."""
from __future__ import annotations

import json
from pathlib import Path

ALL = ["X1200W", "X2200W", "X3200W", "X4200W"]
X32 = ["X3200W", "X4200W"]
X22 = ["X2200W", "X3200W", "X4200W"]
AURO = ["X3200W", "X4200W"]  # Auro typically higher / upgrade


def C(id, section, label, kind, models=None, **kw):
    d = {
        "id": id,
        "section": section,
        "label": label,
        "kind": kind,
        "models": list(models or ALL),
        "x1200w": "X1200W" in (models or ALL),
    }
    d.update(kw)
    return d


sections = [
    # HA denonavr-style: primary media-player surface first
    {"id": "main", "label": "Receiver"},
    {"id": "zone2", "label": "Zone 2"},
    {"id": "zone3", "label": "Zone 3"},
    {"id": "sound", "label": "Sound Mode"},
    {"id": "input", "label": "Input"},
    {"id": "levels", "label": "Channel Levels"},
    {"id": "audio", "label": "Audio"},
    {"id": "video", "label": "Video"},
    {"id": "timers", "label": "Timers"},
    {"id": "tuner", "label": "Tuner"},
    {"id": "media", "label": "Media"},
    {"id": "system", "label": "System"},
    {"id": "advanced", "label": "Advanced"},
]

controls = []

# ---- Main (HA media player essentials) ----
controls += [
    C(
        "pw_power",
        "main",
        "Power",
        "toggle",
        featured=True,
        query="PW?",
        on_command="PWON",
        off_command="PWSTANDBY",
        on_label="On",
        off_label="Standby",
        on_values=["PWON"],
        off_values=["PWSTANDBY"],
    ),
    C(
        "mv_master",
        "main",
        "Volume",
        "stepper",
        featured=True,
        query="MV?",
        prefix="MV",
        min=0,
        max=98,
        pad=2,
        zero_db=80,
        half_step=True,
        up="MVUP",
        down="MVDOWN",
        # HA maps −80..+18 dB; allow direct set via slider in UI
        volume_slider=True,
    ),
    C(
        "mu_mute",
        "main",
        "Mute",
        "toggle",
        featured=True,
        query="MU?",
        on_command="MUON",
        off_command="MUOFF",
        on_label="Muted",
        off_label="Unmuted",
        on_values=["MUON"],
        off_values=["MUOFF"],
    ),
    C(
        "si_select",
        "main",
        "Source",
        "enum",
        featured=True,
        query="SI?",
        options=[
            {"label": l, "command": f"SI{c}", "models": m} for c, l, m in [
                ("PHONO", "Phono", X22),
                ("CD", "CD", ALL),
                ("TUNER", "Tuner", ALL),
                ("DVD", "DVD", ALL),
                ("BD", "Blu-ray", ALL),
                ("TV", "TV Audio", ALL),
                ("SAT/CBL", "CBL/SAT", ALL),
                ("MPLAY", "Media Player", ALL),
                ("GAME", "Game", ALL),
                ("NET", "Online Music", ALL),
                ("IRADIO", "Internet Radio", ALL),
                ("SERVER", "Media Server", ALL),
                ("FAVORITES", "Favorites", ALL),
                ("AUX1", "AUX1", ALL),
                ("AUX2", "AUX2", ALL),
                ("BT", "Bluetooth", ALL),
                ("USB/IPOD", "iPod/USB", ALL),
                ("USB", "USB", ALL),
                ("PANDORA", "Pandora", ALL),
                ("SIRIUSXM", "SiriusXM", ALL),
            ]
        ],
    ),
    C(
        "ms_select",
        "main",
        "Sound Mode",
        "enum",
        featured=True,
        query="MS?",
        options=[
            {"label": l, "command": f"MS{c}"}
            for c, l in [
                ("MOVIE", "Movie"),
                ("MUSIC", "Music"),
                ("GAME", "Game"),
                ("DIRECT", "Direct"),
                ("PURE DIRECT", "Pure Direct"),
                ("STEREO", "Stereo"),
                ("AUTO", "Auto"),
                ("DOLBY DIGITAL", "Dolby Digital"),
                ("DOLBY SURROUND", "Dolby Surround"),
                ("DOLBY ATMOS", "Dolby Atmos"),
                ("DOLBY D+", "Dolby Digital Plus"),
                ("DOLBY HD", "Dolby TrueHD"),
                ("DTS SURROUND", "DTS Surround"),
                ("DTS:X", "DTS:X"),
                ("DTS HD", "DTS-HD"),
                ("DTS HD MSTR", "DTS-HD Master"),
                ("NEURAL:X", "Neural:X"),
                ("MULTI CH IN", "Multi Ch In"),
                ("MCH STEREO", "Multi Ch Stereo"),
                ("ROCK ARENA", "Rock Arena"),
                ("JAZZ CLUB", "Jazz Club"),
                ("MONO MOVIE", "Mono Movie"),
                ("MATRIX", "Matrix"),
                ("VIDEO GAME", "Video Game"),
                ("VIRTUAL", "Virtual"),
            ]
        ],
    ),
    C(
        "ps_dyneq",
        "main",
        "Dynamic EQ",
        "toggle",
        featured=True,
        query="PSDYNEQ ?",
        on_command="PSDYNEQ ON",
        off_command="PSDYNEQ OFF",
        on_label="On",
        off_label="Off",
    ),
    C(
        "zm_power",
        "main",
        "Main Zone",
        "toggle",
        query="ZM?",
        on_command="ZMON",
        off_command="ZMOFF",
        on_label="On",
        off_label="Off",
        on_values=["ZMON"],
        off_values=["ZMOFF"],
    ),
]

# ---- Input (extras beyond Source on Main) ----
controls.append(
    C(
        "sd_mode",
        "input",
        "Input Mode",
        "enum",
        query="SD?",
        options=[
            {"label": "Auto", "command": "SDAUTO"},
            {"label": "HDMI", "command": "SDHDMI"},
            {"label": "Digital", "command": "SDDIGITAL"},
            {"label": "Analog", "command": "SDANALOG"},
            {"label": "ARC", "command": "SDARC"},
        ],
    )
)
controls.append(
    C(
        "dc_mode",
        "input",
        "Decode Mode",
        "enum",
        query="DC?",
        options=[
            {"label": "Auto", "command": "DCAUTO"},
            {"label": "PCM", "command": "DCPCM"},
            {"label": "DTS", "command": "DCDTS"},
        ],
    )
)
controls.append(
    C(
        "sv_video_select",
        "input",
        "Video Select",
        "toggle",
        query="SV?",
        on_command="SVON",
        off_command="SVOFF",
        on_label="On",
        off_label="Off",
        on_values=["SVON"],
        off_values=["SVOFF"],
    )
)

# ---- Sound mode extras (Quick Select / Auro — full list lives on Main) ----
controls.append(
    C(
        "ms_auro",
        "sound",
        "Auro Mode",
        "enum",
        models=AURO,
        query="MS?",
        options=[
            {"label": "Auro-3D", "command": "MSAURO3D"},
            {"label": "Auro-2D Surround", "command": "MSAURO2DSURR"},
        ],
    )
)
controls.append(
    C(
        "ms_quick",
        "sound",
        "Quick Select",
        "enum",
        options=[
            {"label": f"Quick Select {i}", "command": f"MSQUICK{i}"}
            for i in range(1, 6)
        ],
    )
)

# ---- Channel levels ----
cv_chs = [
    ("FL", "Front L", ALL),
    ("FR", "Front R", ALL),
    ("C", "Center", ALL),
    ("SW", "Subwoofer", ALL),
    ("SW2", "Subwoofer 2", X22),
    ("SL", "Surround L", ALL),
    ("SR", "Surround R", ALL),
    ("SBL", "Surround Back L", ALL),
    ("SBR", "Surround Back R", ALL),
    ("SB", "Surround Back", ALL),
    ("FHL", "Front Height L", ALL),
    ("FHR", "Front Height R", ALL),
    ("TFL", "Top Front L", ALL),
    ("TFR", "Top Front R", ALL),
    ("TML", "Top Middle L", ALL),
    ("TMR", "Top Middle R", ALL),
    ("FDL", "Front Dolby L", ALL),
    ("FDR", "Front Dolby R", ALL),
    ("SDL", "Surround Dolby L", ALL),
    ("SDR", "Surround Dolby R", ALL),
]
for code, label, models in cv_chs:
    controls.append(
        C(
            f"cv_{code.lower()}",
            "levels",
            label,
            "slider",
            models=models,
            prefix=f"CV{code}",
            query="CV?",
            min=38,
            max=62,
            pad=2,
            zero_db=50,
            space_before_value=True,
            up=f"CV{code} UP",
            down=f"CV{code} DOWN",
        )
    )

# ---- Audio (tone / audyssey) ----
controls += [
    C(
        "ps_tone",
        "audio",
        "Tone Control",
        "toggle",
        query="PSTONE CTRL ?",
        on_command="PSTONE CTRL ON",
        off_command="PSTONE CTRL OFF",
        on_label="On",
        off_label="Off",
    ),
    C(
        "ps_bas",
        "audio",
        "Bass",
        "slider",
        prefix="PSBAS",
        query="PSBAS ?",
        min=44,
        max=56,
        pad=2,
        zero_db=50,
        space_before_value=True,
        up="PSBAS UP",
        down="PSBAS DOWN",
    ),
    C(
        "ps_tre",
        "audio",
        "Treble",
        "slider",
        prefix="PSTRE",
        query="PSTRE ?",
        min=44,
        max=56,
        pad=2,
        zero_db=50,
        space_before_value=True,
        up="PSTRE UP",
        down="PSTRE DOWN",
    ),
    C(
        "ps_cinema_eq",
        "audio",
        "Cinema EQ",
        "toggle",
        query="PSCINEMA EQ. ?",
        on_command="PSCINEMA EQ.ON",
        off_command="PSCINEMA EQ.OFF",
        on_label="On",
        off_label="Off",
    ),
    C(
        "ps_multeq",
        "audio",
        "MultEQ XT",
        "enum",
        query="PSMULTEQ: ?",
        options=[
            {"label": "Audyssey", "command": "PSMULTEQ:AUDYSSEY"},
            {"label": "Bypass L/R", "command": "PSMULTEQ:BYP.LR"},
            {"label": "Flat", "command": "PSMULTEQ:FLAT"},
            {"label": "Off", "command": "PSMULTEQ:OFF"},
        ],
    ),
    # Dynamic EQ lives on Main (HA denonavr primary action)
    C(
        "ps_dynvol",
        "audio",
        "Dynamic Volume",
        "enum",
        query="PSDYNVOL ?",
        options=[
            {"label": "Heavy", "command": "PSDYNVOL HEV"},
            {"label": "Medium", "command": "PSDYNVOL MED"},
            {"label": "Light", "command": "PSDYNVOL LIT"},
            {"label": "Off", "command": "PSDYNVOL OFF"},
        ],
    ),
    C(
        "ps_geq",
        "audio",
        "Graphic EQ",
        "toggle",
        query="PSGEQ ?",
        on_command="PSGEQ ON",
        off_command="PSGEQ OFF",
        on_label="On",
        off_label="Off",
    ),
    C(
        "ps_drc",
        "audio",
        "Dynamic Compression",
        "enum",
        query="PSDRC ?",
        options=[
            {"label": "Auto", "command": "PSDRC AUTO"},
            {"label": "Low", "command": "PSDRC LOW"},
            {"label": "Mid", "command": "PSDRC MID"},
            {"label": "High", "command": "PSDRC HI"},
            {"label": "Off", "command": "PSDRC OFF"},
        ],
    ),
    C(
        "ps_lfe",
        "audio",
        "LFE",
        "slider",
        prefix="PSLFE",
        query="PSLFE ?",
        min=0,
        max=10,
        pad=2,
        space_before_value=True,
        up="PSLFE UP",
        down="PSLFE DOWN",
    ),
]

# ---- Video ----
controls += [
    C(
        "vs_audio",
        "video",
        "HDMI Audio Out",
        "enum",
        query="VSAUDIO ?",
        options=[
            {"label": "AVR", "command": "VSAUDIO AMP"},
            {"label": "TV", "command": "VSAUDIO TV"},
        ],
    ),
    C(
        "vs_asp",
        "video",
        "Aspect",
        "enum",
        query="VSASP ?",
        options=[
            {"label": "4:3", "command": "VSASPNRM"},
            {"label": "16:9", "command": "VSASPFUL"},
        ],
    ),
    C(
        "vs_sc",
        "video",
        "Resolution",
        "enum",
        query="VSSC ?",
        options=[
            {"label": "Auto", "command": "VSSCAUTO"},
            {"label": "4K", "command": "VSSC4K"},
            {"label": "1080p", "command": "VSSC10P"},
            {"label": "1080i", "command": "VSSC10I"},
            {"label": "720p", "command": "VSSC72P"},
            {"label": "480p/576p", "command": "VSSC48P"},
        ],
    ),
    C(
        "vs_vpm",
        "video",
        "Video Mode",
        "enum",
        query="VSVPM ?",
        options=[
            {"label": "Auto", "command": "VSVPMAUTO"},
            {"label": "Game", "command": "VSVPMGAME"},
            {"label": "Movie", "command": "VSVPMMOVI"},
        ],
    ),
]

# ---- Timers ----
controls += [
    C(
        "slp_timer",
        "timers",
        "Sleep Timer",
        "stepper",
        query="SLP?",
        prefix="SLP",
        min=0,
        max=120,
        pad=3,
        off_command="SLPOFF",
        unit="min",
    ),
    C(
        "eco_mode",
        "timers",
        "ECO Mode",
        "enum",
        query="ECO?",
        options=[
            {"label": "On", "command": "ECOON"},
            {"label": "Auto", "command": "ECOAUTO"},
            {"label": "Off", "command": "ECOOFF"},
        ],
    ),
    C(
        "stby_auto",
        "timers",
        "Auto Standby",
        "enum",
        query="STBY?",
        options=[
            {"label": "15 min", "command": "STBY15M"},
            {"label": "30 min", "command": "STBY30M"},
            {"label": "60 min", "command": "STBY60M"},
            {"label": "Off", "command": "STBYOFF"},
        ],
    ),
]

# ---- Zone 2 ----
z2_inputs = [
    ("SOURCE", "Source"),
    ("CD", "CD"),
    ("TUNER", "Tuner"),
    ("DVD", "DVD"),
    ("BD", "Blu-ray"),
    ("TV", "TV Audio"),
    ("SAT/CBL", "CBL/SAT"),
    ("MPLAY", "Media Player"),
    ("GAME", "Game"),
    ("NET", "Online Music"),
    ("IRADIO", "Internet Radio"),
    ("SERVER", "Media Server"),
    ("FAVORITES", "Favorites"),
    ("AUX1", "AUX1"),
    ("AUX2", "AUX2"),
    ("BT", "Bluetooth"),
    ("USB/IPOD", "iPod/USB"),
]
controls += [
    C(
        "z2_power",
        "zone2",
        "ZONE2 Power",
        "toggle",
        query="Z2?",
        on_command="Z2ON",
        off_command="Z2OFF",
        on_label="On",
        off_label="Off",
        on_values=["Z2ON"],
        off_values=["Z2OFF"],
    ),
    C(
        "z2_input",
        "zone2",
        "ZONE2 Source",
        "enum",
        query="Z2?",
        options=[{"label": l, "command": f"Z2{c}"} for c, l in z2_inputs],
    ),
    C(
        "z2_vol",
        "zone2",
        "ZONE2 Volume",
        "stepper",
        query="Z2?",
        prefix="Z2",
        min=0,
        max=98,
        pad=2,
        zero_db=80,
        half_step=True,
        up="Z2UP",
        down="Z2DOWN",
    ),
    C(
        "z2_mute",
        "zone2",
        "ZONE2 Mute",
        "toggle",
        query="Z2MU?",
        on_command="Z2MUON",
        off_command="Z2MUOFF",
        on_label="Muted",
        off_label="Unmuted",
        on_values=["Z2MUON"],
        off_values=["Z2MUOFF"],
    ),
]

# ---- Zone 3 (X3200W / X4200W) ----
controls += [
    C(
        "z3_power",
        "zone3",
        "ZONE3 Power",
        "toggle",
        models=X32,
        query="Z3?",
        on_command="Z3ON",
        off_command="Z3OFF",
        on_label="On",
        off_label="Off",
        on_values=["Z3ON"],
        off_values=["Z3OFF"],
    ),
    C(
        "z3_input",
        "zone3",
        "ZONE3 Source",
        "enum",
        models=X32,
        query="Z3?",
        options=[{"label": l, "command": f"Z3{c}"} for c, l in z2_inputs],
    ),
    C(
        "z3_vol",
        "zone3",
        "ZONE3 Volume",
        "stepper",
        models=X32,
        query="Z3?",
        prefix="Z3",
        min=0,
        max=98,
        pad=2,
        zero_db=80,
        up="Z3UP",
        down="Z3DOWN",
    ),
    C(
        "z3_mute",
        "zone3",
        "ZONE3 Mute",
        "toggle",
        models=X32,
        query="Z3MU?",
        on_command="Z3MUON",
        off_command="Z3MUOFF",
        on_label="Muted",
        off_label="Unmuted",
        on_values=["Z3MUON"],
        off_values=["Z3MUOFF"],
    ),
]

# ---- Tuner ----
controls += [
    C(
        "tm_band",
        "tuner",
        "Band",
        "enum",
        query="TMAN?",
        options=[
            {"label": "AM", "command": "TMANAM"},
            {"label": "FM", "command": "TMANFM"},
        ],
    ),
    C(
        "tf_tune",
        "tuner",
        "Frequency",
        "stepper",
        query="TFAN?",
        up="TFANUP",
        down="TFANDOWN",
        display_only_value=True,
    ),
    C(
        "tp_preset",
        "tuner",
        "Preset",
        "stepper",
        query="TPAN?",
        up="TPANUP",
        down="TPANDOWN",
        display_only_value=True,
    ),
]

# ---- Media (compact transport) ----
for cmd, label in [
    ("NS9A", "Play"),
    ("NS9B", "Pause"),
    ("NS9C", "Stop"),
    ("NS9D", "Skip +"),
    ("NS9E", "Skip −"),
    ("NS94", "Enter"),
    ("NS90", "Up"),
    ("NS91", "Down"),
    ("NS92", "Left"),
    ("NS93", "Right"),
]:
    controls.append(C(f"ns_{cmd.lower()}", "media", label, "action", command=cmd))

# ---- System ----
controls += [
    C(
        "dimmer",
        "system",
        "Dimmer",
        "enum",
        query="DIM ?",
        options=[
            {"label": "Bright", "command": "DIM BRI"},
            {"label": "Dim", "command": "DIM DIM"},
            {"label": "Dark", "command": "DIM DAR"},
            {"label": "Off", "command": "DIM OFF"},
        ],
    ),
    C(
        "mn_menu",
        "system",
        "Setup Menu",
        "toggle",
        query="MNMEN?",
        on_command="MNMEN ON",
        off_command="MNMEN OFF",
        on_label="On",
        off_label="Off",
    ),
    C(
        "mn_zst",
        "system",
        "All Zone Stereo",
        "toggle",
        query="MNZST?",
        on_command="MNZST ON",
        off_command="MNZST OFF",
        on_label="On",
        off_label="Off",
        confirm=True,
        confirm_message="Change All Zone Stereo?",
    ),
]
for cmd, label in [
    ("MNCUP", "Cursor Up"),
    ("MNCDN", "Cursor Down"),
    ("MNCLT", "Cursor Left"),
    ("MNCRT", "Cursor Right"),
    ("MNENT", "Enter"),
    ("MNRTN", "Return"),
]:
    controls.append(C(f"mn_{cmd.lower()}", "system", label, "action", command=cmd))

controls.append(C("raw_command", "advanced", "Raw Command", "raw", allow_raw=True))

status_queries = [
    "PW?",
    "ZM?",
    "MV?",
    "MU?",
    "SI?",
    "SD?",
    "DC?",
    "SV?",
    "MS?",
    "CV?",
    "SLP?",
    "STBY?",
    "ECO?",
    "Z2?",
    "Z2MU?",
    "Z3?",
    "Z3MU?",
    "PSTONE CTRL ?",
    "PSBAS ?",
    "PSTRE ?",
    "PSCINEMA EQ. ?",
    "PSMULTEQ: ?",
    "PSDYNEQ ?",
    "PSDYNVOL ?",
    "PSGEQ ?",
    "PSDRC ?",
    "PSLFE ?",
    "VSASP ?",
    "VSSC ?",
    "VSAUDIO ?",
    "VSVPM ?",
    "TMAN?",
    "TFAN?",
    "TPAN?",
    "MNMEN?",
    "MNZST?",
    "DIM ?",
]

status_queries_lite = [
    "PW?",
    "ZM?",
    "MV?",
    "MU?",
    "SI?",
    "MS?",
    "SLP?",
    "ECO?",
    "Z2?",
]

section_queries = {
    # HA-style primary surface
    "main": ["PW?", "ZM?", "MV?", "MU?", "SI?", "MS?", "PSDYNEQ ?"],
    "input": ["SD?", "DC?", "SV?"],
    "sound": ["MS?"],
    "levels": ["CV?"],
    "audio": [
        "PSTONE CTRL ?",
        "PSBAS ?",
        "PSTRE ?",
        "PSCINEMA EQ. ?",
        "PSMULTEQ: ?",
        "PSDYNVOL ?",
        "PSGEQ ?",
        "PSDRC ?",
        "PSLFE ?",
    ],
    "video": ["VSASP ?", "VSSC ?", "VSAUDIO ?", "VSVPM ?"],
    "timers": ["SLP?", "STBY?", "ECO?"],
    "zone2": ["Z2?", "Z2MU?"],
    "zone3": ["Z3?", "Z3MU?"],
    "tuner": ["TMAN?", "TFAN?", "TPAN?"],
    "system": ["MNMEN?", "MNZST?", "DIM ?"],
}

out = {
    "model": "AVR-X1200W",
    "protocol_version": "02",
    "source": "DENON-X1200W-TELNET.pdf",
    "supported_models": [f"AVR-{m}" for m in ALL],
    "sections": sections,
    "controls": controls,
    "status_queries": status_queries,
    "status_queries_lite": status_queries_lite,
    "section_queries": section_queries,
    "blocked_commands": ["RM STA", "RM END"],
    "confirm_prefixes": [
        "SYREMOTE LOCK",
        "SYPANEL LOCK",
        "SYPANEL+V LOCK",
        "MNZST",
        "CVZRL",
        "TPANMEM",
    ],
}

path = Path("protocol/telnet_commands.json")
path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Wrote {path}: {len(controls)} controls, {len(sections)} sections")
