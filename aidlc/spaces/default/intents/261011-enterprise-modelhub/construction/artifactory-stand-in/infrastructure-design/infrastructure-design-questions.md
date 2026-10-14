# Infrastructure Design Questions: artifactory-stand-in

No open questions. The stand-in is never deployed: it runs inside the test process on the build machines, so it needs no server, container, network, secret or monitoring of its own. The design records that plainly and shows how it is built, tested and kept out of what is delivered. The real hosting questions (entry point, TLS, volumes, registry) are asked in the `platform` unit.
