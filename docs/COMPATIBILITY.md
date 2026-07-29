# Compatibility

## Tested

| Model | Notes |
|-------|--------|
| **Denon AVR-X1200W** | Primary target. Firmware family observed during development: `4700-0591-7045`. |

## Likely similar

Other Denon / Marantz units from the same generation that use the **SETUP** frameset web UI (`/SETUP/.../*.asp`) may work with little or no change.

Differences to expect:

- Extra / missing speakers (Amp Assign)  
- Different Manual EQ channel lists  
- Menu labels / grey rules  
- Network / firmware page layout  

## Probably different

Newer AVRs that use **modern Web Control** (e.g. `/ajax/...` JSON APIs on other ports) need a separate client — this project speaks the **legacy SETUP HTML forms**.

## Telnet

Official telnet commands remain useful for day-to-day HA integrations (volume, input, power).  
They are **not** a substitute for Manual EQ band control on the X1200W.

## Reporting success

Open an issue with: model, firmware version, what worked, what 404’d or looked wrong.
