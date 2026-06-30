from pysnmp.hlapi.asyncio import (
    bulk_walk_cmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)

snmpEngine = SnmpEngine() # Integra tutta la logica necessaria per inviare e ricevere messaggi SNMP


async def snmp_walk_asincrona(host: str, port: int, community: str, oid: str, timeout: float = 2.0, retries: int = 1, maxRep: int = 20) -> dict[int, str]:
    risultati: dict[int, str] = {}

    communicationChannel = await UdpTransportTarget.create((host, port), timeout, retries)

    async for errorIndication, errorStatus, errorIndex, varBinds in bulk_walk_cmd(
        snmpEngine,
        CommunityData(community, mpModel = 1),
        communicationChannel,
        ContextData(),
        ObjectType(ObjectIdentity(oid)), 
        lexicographicMode=False,
        lookupMib=False,
        maxRep = maxRep,
    ):
        if errorIndication:
            raise RuntimeError(f"[{host}] SNMP error: {errorIndication}")

        if errorStatus:
            raise RuntimeError(
                f"[{host}] SNMP error: {errorStatus.prettyPrint()} "
                f"at index {errorIndex}"
            )
        
        for oidResponse, value in varBinds:
            oidResponse = str(oidResponse)

            if not oidResponse.startswith(oid + "."):
                continue

            idx = int(oidResponse.removeprefix(oid + "."))
            risultati[idx] = value.prettyPrint()

    return risultati