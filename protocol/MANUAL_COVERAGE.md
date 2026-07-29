# AVR-X1200W manual vs SETUP web crawl coverage

- Protocol pages: **144**
- Catalog endpoints: **44**
- Crawled: **39** · Missing: **0** · Blocked/stub: **3**

| Section | Item | Status | Note |
|---------|------|--------|------|
| Audio | Dialog Level | CRAWLED | audio_dialoglevel_s_audio |
| Audio | Subwoofer Level | CRAWLED | audio_subwooferlevel_s_audio |
| Audio | Surr.Parameter | CRAWLED | audio_surroundparameter_s_audio |
| Audio | Restorer | CRAWLED | audio_restorer_s_audio |
| Audio | Audio Delay | CRAWLED | audio_audiodelay_s_audio |
| Audio | Volume | CRAWLED | audio_volume_s_audio |
| Audio | Audyssey (MultEQ/DynEQ/DynVol settings) | CRAWLED | audio_audyssey_s_audio |
| Audio | Manual EQ | CRAWLED | audio_graphiceq_s_audio |
| Video | HDMI Setup | CRAWLED | video_hdmisetup_s_video |
| Video | On Screen Disp. | CRAWLED | video_onscreendisplay_s_video |
| Video | TV Format | CRAWLED | video_tvformat_s_video |
| Inputs | Input Assign | CRAWLED | inputs_inputassign_s_inputassign |
| Inputs | Source Rename | CRAWLED | inputs_sourcerename_s_rename |
| Inputs | Hide Sources | CRAWLED | inputs_hidesources_s_delete |
| Inputs | Source Level | CRAWLED | inputs_sourcelevel_s_inputsetup |
| Inputs | Input Select | CRAWLED | inputs_inputselect_s_inputsetup |
| Speakers | Audyssey Setup (wizard) | STUB_ONLY_NO_WIZARD | Do not start. Future engage toggle only; mic wizard is OSD. |
| Speakers | Manual Setup / Amp Assign | CRAWLED | speakers_ampassign_s_speakersetup |
| Speakers | Manual Setup / Speaker Config. | CRAWLED | speakers_speakerconfig_s_speakersetup |
| Speakers | Manual Setup / Distances | CRAWLED | speakers_distances_s_speakersetup |
| Speakers | Manual Setup / Levels | CRAWLED | speakers_levels_s_speakersetup |
| Speakers | Manual Setup / Crossovers | CRAWLED | speakers_crossovers_s_speakersetup |
| Speakers | Manual Setup / Bass | CRAWLED | speakers_bass_s_speakersetup |
| Speakers | Manual Setup / Front Speaker | CRAWLED | speakers_frontspeaker_s_speakersetup |
| Network | Information | CRAWLED | via NETWORK/SETTINGS (+ /api/info/network) |
| Network | Connection | CRAWLED | network_connection_r_network_setting_dhcp, network_connection_s_network_setting_dhcp |
| Network | Settings | CRAWLED | network_settings_s_network_setting_dhcp, network_settings_r_network_setting_dhcp |
| Network | Network Control | CRAWLED | network_ipcontrol_s_network |
| Network | Friendly Name | CRAWLED | network_friendlyname_s_network |
| Network | Diagnostics | CRAWLED | network_diagnostics_s_network, NETWORK/DIAGNOSTICS |
| Network | Maintenance Mode | BLOCKED | Service technician mode — excluded |
| General | Language | CRAWLED | general_language_s_general |
| General | ECO | CRAWLED | general_eco_s_general |
| General | ZONE2 Setup | CRAWLED | general_zone2setup_s_general |
| General | Zone Rename | CRAWLED | general_zonerename_s_general |
| General | Quick Sel.Names | CRAWLED | general_selectnames_s_general |
| General | Front Display | CRAWLED | general_frontdisplay_s_general |
| General | Firmware (info only) | CRAWLED | general_firmware_r_firmware, general_firmware_s_firmware |
| General | Information | CRAWLED | general_information_s_information, GENERAL/INFORMATION |
| General | Usage Data | CRAWLED | general_usagedata_s_general |
| General | Setup Lock (read scrape only) | CRAWLED | general_setuplock_s_general |
| Setup Assistant | Begin Setup / wizards | BLOCKED | Setup Assistant wizards excluded |

## Limits
- No Save/Load
- No firmware update / web update / add feature
- No Setup Lock writes
- No network IP/DHCP/proxy writes
- No Audyssey Setup wizard start (engage stub only later)
- No Maintenance Mode
- No Setup Assistant
- Restore any temporary toggle used while scraping

## Future API stub (not implemented in this crawl phase)
- `POST /api/speakers/audyssey-setup/engage` — engage toggle only; never starts the mic wizard.