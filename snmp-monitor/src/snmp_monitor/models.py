from dataclasses import dataclass
from datetime import datetime

@dataclass
class InterfaceMetric:
    timestamp: datetime
    agent: str
    if_index: int
    if_name: str
    if_status: str        # "up" o "down"
    in_octets: int
    out_octets: int
    in_errors: int
    out_errors: int
    in_mbps: float = 0.0  # calcolato dopo, default 0
    out_mbps: float = 0.0

@dataclass
class SystemInfo:
    #Informazioni base lette dal gruppo system della MIB-II.
    #Questa dataclass viene usata nello STEP 02.

    agent_name: str
    host: str
    port: int
    sys_descr: str
    sys_uptime: str
    sys_name: str

@dataclass
class TrapEvent:
    timestamp: datetime
    source_ip: str
    trap_type: str        # "linkDown", "linkUp", ecc.
    varbinds: dict

@dataclass
class AgentConfig:
    name: str # Identifica l'agente, ad esempio "Router1"
    host: str # Indirizzo IP
    port: int  # Porta SNMP (default 161)
    community: str # Autorizza la lettura dei dati
