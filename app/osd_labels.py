"""Denon OSD / front-panel style human-readable labels (AVR-X1200W family).

Mapped from Denon control protocol Ver.02 codes to names shown in the
receiver OSD / INFO strip and owner's manuals (sound modes, inputs, etc.).
"""

from __future__ import annotations

from typing import Dict, Optional

# Surround / sound mode (MS*) — Denon OSD wording
SOUND_MODES: Dict[str, str] = {
    "MSMOVIE": "Movie",
    "MSMUSIC": "Music",
    "MSGAME": "Game",
    "MSDIRECT": "Direct",
    "MSDSD DIRECT": "DSD Direct",
    "MSPURE DIRECT": "Pure Direct",
    "MSDSD PURE DIRECT": "DSD Pure Direct",
    "MSSTEREO": "Stereo",
    "MSAUTO": "Auto",
    "MSDOLBY DIGITAL": "Dolby Digital",
    "MSDOLBY SURROUND": "Dolby Surround",
    "MSDOLBY ATMOS": "Dolby Atmos",
    "MSDOLBY D EX": "Dolby Digital EX",
    "MSDOLBY D+DS": "Dolby Digital + Dolby Surround",
    "MSDOLBY D+": "Dolby Digital Plus",
    "MSDOLBY D+ +DS": "Dolby Digital Plus + Dolby Surround",
    "MSDOLBY HD": "Dolby TrueHD",
    "MSDOLBY HD+DS": "Dolby TrueHD + Dolby Surround",
    "MSDTS SURROUND": "DTS Surround",
    "MSDTS ES DSCRT6.1": "DTS-ES Discrete 6.1",
    "MSDTS ES MTRX6.1": "DTS-ES Matrix 6.1",
    "MSDTS96/24": "DTS 96/24",
    "MSDTS96 ES MTRX": "DTS 96/24 ES Matrix",
    "MSDTS+NEURAL:X": "DTS + Neural:X",
    "MSDTS ES MTRX+NEURAL:X": "DTS-ES Matrix + Neural:X",
    "MSDTS ES DSCRT+NEURAL:X": "DTS-ES Discrete + Neural:X",
    "MSDTS HD": "DTS-HD",
    "MSDTS HD MSTR": "DTS-HD Master Audio",
    "MSDTS HD+NEURAL:X": "DTS-HD + Neural:X",
    "MSDTS:X": "DTS:X",
    "MSDTS:X MSTR": "DTS:X Master",
    "MSDTS EXPRESS": "DTS Express",
    "MSDTS ES 8CH DSCRT": "DTS-ES 8ch Discrete",
    "MSNEURAL:X": "Neural:X",
    "MSMULTI CH IN": "Multi Ch In",
    "MSM CH IN+DS": "Multi Ch In + Dolby Surround",
    "MSMULTI CH IN 7.1": "Multi Ch In 7.1",
    "MSM CH IN+NEURAL:X": "Multi Ch In + Neural:X",
    "MSAUDYSSEY DSX": "Audyssey DSX",
    "MSMCH STEREO": "Multi Ch Stereo",
    "MSROCK ARENA": "Rock Arena",
    "MSJAZZ CLUB": "Jazz Club",
    "MSMONO MOVIE": "Mono Movie",
    "MSMATRIX": "Matrix",
    "MSVIDEO GAME": "Video Game",
    "MSVIRTUAL": "Virtual",
    "MSLEFT": "Balance Left",
    "MSRIGHT": "Balance Right",
    "MSQUICK1": "Quick Select 1",
    "MSQUICK2": "Quick Select 2",
    "MSQUICK3": "Quick Select 3",
    "MSQUICK4": "Quick Select 4",
    "MSQUICK5": "Quick Select 5",
}

# Input sources (SI*) — Denon source names on OSD / front panel
INPUTS: Dict[str, str] = {
    "SIPHONO": "Phono",
    "SICD": "CD",
    "SITUNER": "Tuner",
    "SIDVD": "DVD",
    "SIBD": "Blu-ray",
    "SITV": "TV Audio",
    "SISAT/CBL": "CBL/SAT",
    "SIMPLAY": "Media Player",
    "SIGAME": "Game",
    "SIHDRADIO": "HD Radio",
    "SINET": "Online Music",
    "SIPANDORA": "Pandora",
    "SISIRIUSXM": "SiriusXM",
    "SISPOTIFY": "Spotify",
    "SILASTFM": "Last.fm",
    "SIFLICKR": "Flickr",
    "SIIRADIO": "Internet Radio",
    "SISERVER": "Media Server",
    "SIFAVORITES": "Favorites",
    "SIAUX1": "AUX1",
    "SIAUX2": "AUX2",
    "SIBT": "Bluetooth",
    "SIUSB/IPOD": "iPod/USB",
    "SIUSB": "USB",
    "SIIPD": "iPod Direct",
    "SIIRP": "iRadio Recent",
    "SIFVP": "Favorites Play",
}

# Channel volume codes → Denon speaker labels
CHANNELS: Dict[str, str] = {
    "FL": "Front L",
    "FR": "Front R",
    "C": "Center",
    "SW": "Subwoofer",
    "SW2": "Subwoofer 2",
    "SL": "Surround L",
    "SR": "Surround R",
    "SBL": "Surround Back L",
    "SBR": "Surround Back R",
    "SB": "Surround Back",
    "FHL": "Front Height L",
    "FHR": "Front Height R",
    "TFL": "Top Front L",
    "TFR": "Top Front R",
    "TML": "Top Middle L",
    "TMR": "Top Middle R",
    "FDL": "Front Dolby L",
    "FDR": "Front Dolby R",
    "SDL": "Surround Dolby L",
    "SDR": "Surround Dolby R",
}

POWER: Dict[str, str] = {
    "PWON": "On",
    "PWSTANDBY": "Standby",
    "ZMON": "Main Zone On",
    "ZMOFF": "Main Zone Off",
    "Z2ON": "ZONE2 On",
    "Z2OFF": "ZONE2 Off",
    "MUON": "Mute",
    "MUOFF": "Unmute",
}

MISC: Dict[str, str] = {
    "SDAUTO": "Auto",
    "SDHDMI": "HDMI",
    "SDDIGITAL": "Digital",
    "SDANALOG": "Analog",
    "SDARC": "TV Audio (ARC)",
    "DCAUTO": "Auto",
    "DCPCM": "PCM",
    "DCDTS": "DTS",
    "SVON": "Video Select On",
    "SVOFF": "Video Select Off",
    "ECOON": "ECO On",
    "ECOAUTO": "ECO Auto",
    "ECOOFF": "ECO Off",
    "STBY15M": "Auto Standby 15 min",
    "STBY30M": "Auto Standby 30 min",
    "STBY60M": "Auto Standby 60 min",
    "STBYOFF": "Auto Standby Off",
    "SLPOFF": "Sleep Off",
    "PSMULTEQ:AUDYSSEY": "MultEQ XT Audyssey",
    "PSMULTEQ:BYP.LR": "MultEQ XT Bypass L/R",
    "PSMULTEQ:FLAT": "MultEQ XT Flat",
    "PSMULTEQ:OFF": "MultEQ XT Off",
    "PSDYNEQ ON": "Dynamic EQ On",
    "PSDYNEQ OFF": "Dynamic EQ Off",
    "PSDYNVOL HEV": "Dynamic Volume Heavy",
    "PSDYNVOL MED": "Dynamic Volume Medium",
    "PSDYNVOL LIT": "Dynamic Volume Light",
    "PSDYNVOL OFF": "Dynamic Volume Off",
    "PSTONE CTRL ON": "Tone Control On",
    "PSTONE CTRL OFF": "Tone Control Off",
    "PSCINEMA EQ.ON": "Cinema EQ On",
    "PSCINEMA EQ.OFF": "Cinema EQ Off",
    "PSGEQ ON": "Graphic EQ On",
    "PSGEQ OFF": "Graphic EQ Off",
    "VSAUDIO AMP": "HDMI Audio → AVR",
    "VSAUDIO TV": "HDMI Audio → TV",
    "DIM BRI": "Dimmer Bright",
    "DIM DIM": "Dimmer Dim",
    "DIM DAR": "Dimmer Dark",
    "DIM OFF": "Dimmer Off",
}


def osd_label(raw: Optional[str]) -> str:
    """Return Denon-style display name for a protocol line or command."""
    if not raw:
        return "—"
    s = str(raw).strip()
    u = s.upper()
    for table in (POWER, SOUND_MODES, INPUTS, MISC):
        if u in table:
            return table[u]
        # try without spaces normalization
        compact = u.replace("  ", " ")
        if compact in table:
            return table[compact]
    # Channel volume CVFL 50
    if u.startswith("CV") and " " in u:
        code = u[2:].split()[0]
        if code in CHANNELS:
            return CHANNELS[code]
    # Sleep SLP030
    if u.startswith("SLP") and u[3:].isdigit():
        return f"Sleep {int(u[3:])} min"
    if u.startswith("Z2SLP") and u[5:].isdigit():
        return f"ZONE2 Sleep {int(u[5:])} min"
    # Master volume
    if u.startswith("MV") and not u.startswith("MVMAX"):
        return s
    # SI / MS / SV already handled; strip prefix for partial
    for prefix, table in (("SI", INPUTS), ("MS", SOUND_MODES), ("SV", None)):
        if u.startswith(prefix) and len(u) > 2:
            key = u if prefix != "SV" else u
            if key in INPUTS:
                return INPUTS[key]
            if key in SOUND_MODES:
                return SOUND_MODES[key]
            if prefix == "SV" and key.startswith("SV"):
                si_key = "SI" + key[2:]
                if si_key in INPUTS:
                    return INPUTS[si_key]
    return s


def channel_osd(code: str) -> str:
    return CHANNELS.get(code.upper(), code)
