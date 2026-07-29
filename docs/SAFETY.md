# Safety policy

DENON AVR MANAGER is designed so a wrong click is unlikely to brick or lock you out of the AVR.

## Hard / soft blocks

Implemented in `app/safety.py` and route handlers:

| Area | Policy |
|------|--------|
| Config Save / Load | Blocked |
| Audyssey Setup wizard steps | Blocked (engage endpoint is acknowledgment-only) |
| Maintenance / Setup Assistant | Blocked |
| Firmware Update / Web Update / Add New Feature | Allowed only via explicit confirmed API/UI actions |
| Network DHCP / IP / Proxy | Allowed only with explicit Save; UI warns about disconnect |
| Setup Lock On/Off | Allowed; when On, other writes return 403 |
| Everyday Setup pages | Allowed (Volume, EQ, Speakers, …) |

## Forced fields on write

Unless you are editing Setup Lock itself, posts force:

- `setPureDirectOn=OFF`  
- `setSetupLock=OFF`  

so a stale browser form cannot accidentally engage Pure Direct or lock the menu mid-edit.

## Operator guidelines

1. Keep a note of your AVR IP and network settings before experimenting.  
2. Prefer reading (`GET .../state`) before writing.  
3. After scrape/probe sessions, confirm critical settings (Manual EQ Off/On, network DHCP) match what you expect.  
4. Do not expose port 8000 to the public internet without authentication / VPN.

## Disclaimer

Unofficial software. You use it at your own risk. The authors are not affiliated with Sound United / Denon / Marantz / Audyssey.
