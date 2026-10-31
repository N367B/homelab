# UPS

HPE T1500 G5 INTL Tower UPS, P/N Q1F52A, S/N 3C88171030, firmware 01.04.0006. It is an Eaton 5P 1550 made by LianZheng for HPE in 2018 (line-interactive, 1550 VA / 1100 W). It was bought second hand, with new Greencell batteries added later.

## Current state

The UPS is faulty and not proven usable as a backup. It protects nothing until it passes a test on battery.

- Status on 27 October 2026 is `ALARM OL` with the outputs on and the battery at 100 %. The alarm has been active without a break since 18 October 10:47.
- Nothing has been tried on battery since the fault came back. The battery test and the mains unplug test are still to do.

- The display shows `AVR tempera. fault` with code `0x105`. The fault log holds 7 entries, all the same.
- During the fault the outputs are cut, so battery tests cannot run.
- The fault is not always there. A power cycle clears it, and it comes back after some time or at startup. Between 12 and 16 October 2026 it stayed on without a break.
- After the restart of 16 October 2026 the UPS ran 35 hours without a fault, from 23:21 to 18 October 10:47. The alarm then came back with the outputs still on (`ALARM OL CHRG`) and the battery at 100 %. At 22:54 the charger status went from `CHRG` to idle and the status stayed `ALARM OL` since. The load is 0 %, so the fault does not depend on a load.
- On battery the UPS switched itself off after a few seconds, even with an empty output.
- Without the fault the battery reads 91 %, 271 min and 40.7 V in float. The fan is loud and the airflow feels normal.

No public document defines `0x105` for this model. The Eaton Callisto 5PX G2 service manual lists it as "AVR Too Hot" ("AVR is abnormal"), a different model on the same platform. A fan failure would be `0x007` there, so the fan looks unlikely. The temperature sensor of the AVR stage or the control board are the main suspects. A real overheat is ruled out, since the UPS runs with no load in a 20 to 25 °C room.

The HPE and Eaton manuals gathered so far do not define the code either. The HPE user guide only says to note the alarm and the serial number and contact service.

## How it is wired

The UPS is read over USB by the edge with NUT (`usbhid-ups`, role `nut`). The edge is not powered by the UPS and must never shut down because of it.

- `upsmon` monitors the UPS with a power value of 0 and `MINSUPPLIES 0`, so a critical UPS never counts toward a shutdown. `SHUTDOWNCMD` only logs a line.
- A systemd timer writes one line per minute to the journal. Read it with `journalctl -t ups-log`. It shows the status, alarm, load, battery and input voltage, which is enough to date each fault.
- There is no NUT admin account yet. It would allow muting the beeper and running battery tests from the edge, so it is worth adding once the UPS works.

On 16 October 2026 the edge shut itself down when the UPS went on battery with its outputs off. The earlier `OFFDURATION -1` setting only covered the outputs being off while on mains. The power value 0 setting replaces it.

## Support

HPE case 5405935426 was opened on 16 October 2026. HPE answered that the unit has been out of warranty since 18 July 2019 and offered a paid diagnostic quote. The quote was declined, the question about `0x105` got no answer, and the case was closed automatically on 20 October 2026. There is no firmware update to look for, the unit already runs 01.04.0006, which is believed to be the latest.

## What was tried and found

Done so far, in order.

- Batteries were replaced with new Greencell ones. The UPS had not been used for months before that.
- The fan blows strongly and there is no obvious dust. When the UPS is unplugged from the mains the fan speed goes up. This points away from a fan fault.
- Power cycling clears the fault for a while. The longest fault-free run seen was 35 hours, from 16 October 23:21 to 18 October 10:47.
- Unplugging the mains on the day of the first test made the UPS go on battery and switch itself off after a few seconds, even with nothing on the outputs. That test has not been repeated since.
- The edge was shut down by `upsmon` during that test, because the UPS went on battery with its outputs off. This is fixed, see above. A real battery event has not happened since, so the fix is checked by its config and the "monitoring only" log line only.
- The HPE case gave nothing, see Support.

Hypotheses, none confirmed.

- A faulty or badly connected temperature sensor on the AVR stage. This fits a fault that comes and goes, appears with no load and in a cool room, and sometimes leaves the outputs on.
- A fault on the control board. The spare is HPE 881764-001.
- A fan fault is unlikely, since the Eaton Callisto 5PX G2 reports it as `0x007`, and the fan runs strong.
- A real overheat is ruled out.

Sources.

- The Callisto 5PX G2 service manual fault table lists `0x105` as "AVR Too Hot", `0x004` as "UPS Temp. High", `0x007` as "Fan Lock" and `0x002` as an internal fault with an abnormal NTC. Its flowchart for 105 ends with replacing the UPS, but the steps could not be read.
- The Eaton PredictPulse alarm list reports a temperature sensor with invalid values as an internal fault.
- No forum post or repair report was found for this fault on a 5P or a T1500 G5.

## Next steps

- Reset the fault from the front menu (`Control > Reset fault state`), restart the UPS, and note the time to see whether the fault comes back by itself.
- Run `Control > Start battery test` with nothing on the outputs, then read `ups-log` for the `OB` status and how long it lasted. A mains unplug test with no load tells the same thing.
- If the UPS switches off on battery or the fault keeps coming back, open the case. Check the temperature sensor and its connector on the AVR stage and the solder joints of the control board. Disconnect the mains and the battery first and wait for the capacitors to discharge. The control board spare is HPE 881764-001, with price and availability unchecked.
- Once the UPS works, add a NUT admin account and the compute node as a NUT client for a clean shutdown at low battery.

## Useful menu paths

The front menu `Control > Reset fault state` clears active faults and needs a UPS restart. `Fault log` lists the stored faults.
