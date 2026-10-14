# Reliability Requirements: import-cli

An import can be stopped and run again at any moment.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR4.2 | Stopping at any moment (Ctrl-C, crash, power loss) and running again gives a correct, complete result. | Tested by killing the process during create, during a piece and during the wait | NFR4, rules BR1.5, BR1.8 |
| NFR4.3 | Network errors are retried five times at 1, 2, 4, 8 and 16 seconds with a little random wait. | Tested with the stand-in's failure switches | NFR4, rule BR1.6 |
| NFR4.4 | When the service is busy the command waits up to 30 minutes, asking every 60 seconds. | Settings busy_wait_minutes and busy_poll_seconds | NFR4, rule BR1.7 |
| NFR3.1 | Not applicable as an availability promise: the command runs when the person runs it. | None | NFR3 |
| NFR10.1 | Import behaves the same on Linux and Windows import computers and needs nothing installed beyond the program or its offline pack. | The import tests run on both against the stand-in | NFR10, rule BR1.12 |
