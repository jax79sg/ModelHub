# Infrastructure Design Questions: portal

No open questions. The two choices that apply to every server unit were answered at the Catalog (one production stack only; alerts routed by the existing central monitoring). The portal's container details follow from the approved targets (4 workers, sessions in memory, one copy). How people reach it (entry point and TLS) is decided in the `platform` unit.
