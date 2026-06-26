# Definizione della classe OID che rappresenta un oggetto OID (Object Identifier) utilizzato per monitorare informazioni

from dataclasses import dataclass

@dataclass(frozen=True)
class OID:
    name: str # È il nome dell'informazione che stiamo leggendo
    value: str # Indica la posizione in cui si trova l'informazione all'interno dell'alber
    kind: str #sysUpTime, ifTable, ifInOctets
    data_type: str # Tipo di dato primitivo che rappresenta l'informazione (INTEGER, OCTET STRING, Counter32, ecc.)
    description: str # Spiega cosa rappresenta quel valore restituito dall'OID
    access: str = "read-only"
    
#OID del gruppo system

SYSTEM_OIDS = {
    "sysDescr": OID(
        name="sysDescr",
        value="1.3.6.1.2.1.1.1.0",
        kind="scalar",
        data_type="OCTET STRING",
        description="Descrizione del dispositivo",
    ),
    "sysUpTime": OID(
        name="sysUpTime",
        value="1.3.6.1.2.1.1.3.0",
        kind="scalar",
        data_type="TimeTicks",
        description="Tempo trascorso dall'avvio dell'agente",
    ),
    "sysName": OID(
        name="sysName",
        value="1.3.6.1.2.1.1.5.0",
        kind="scalar",
        data_type="OCTET STRING",
        description="Nome del dispositivo",
    ),
}

#OID della ifTable

IF_TABLE_OIDS = {
    "ifIndex": OID(
        name="ifIndex",
        value="1.3.6.1.2.1.2.2.1.1",
        kind="table_column",
        data_type="INTEGER",
        description="Indice dell'interfaccia",
    ),
    "ifDescr": OID(
        name="ifDescr",
        value="1.3.6.1.2.1.2.2.1.2",
        kind="table_column",
        data_type="OCTET STRING",
        description="Descrizione dell'interfaccia",
    ),
    "ifOperStatus": OID(
        name="ifOperStatus",
        value="1.3.6.1.2.1.2.2.1.8",
        kind="table_column",
        data_type="INTEGER",
        description="Stato operativo dell'interfaccia",
    ),
    "ifInOctets": OID(
        name="ifInOctets",
        value="1.3.6.1.2.1.2.2.1.10",
        kind="table_column",
        data_type="Counter32",
        description="Byte ricevuti dall'interfaccia",
    ),
    "ifOutOctets": OID(
        name="ifOutOctets",
        value="1.3.6.1.2.1.2.2.1.16",
        kind="table_column",
        data_type="Counter32",
        description="Byte inviati dall'interfaccia",
    ),
}