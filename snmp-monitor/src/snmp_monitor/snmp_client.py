import asyncio
from pysnmp.hlapi.asyncio import (
    walk_cmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)


def snmp_walk(host: str, port: int, community: str, oid: str):
    """
    Esegue una richiesta SNMP WALK verso l'agente specificato.
    """
    return asyncio.run(snmp_walk_asincrona(host, port, community, oid))


async def snmp_walk_asincrona(host: str, port: int, community: str, oid: str):
    risultati = {}

    communicationChannel = await UdpTransportTarget.create((host, port))

    async for errorIndication, errorStatus, errorIndex, varBinds in walk_cmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        communicationChannel,
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False,
        lookupMib=False,
    ):
        if errorIndication:
            raise RuntimeError(errorIndication)

        if errorStatus:
            raise RuntimeError(f"{errorStatus.prettyPrint()} at {errorIndex}")

        for oidResponse, value in varBinds:
            oidResponse = str(oidResponse)

            if not oidResponse.startswith(oid + "."):
                continue

            idx = int(oidResponse.removeprefix(oid + "."))
            risultati[idx] = value.prettyPrint()

    return risultati