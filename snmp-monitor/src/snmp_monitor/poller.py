import time
from datetime import datetime

from snmp_monitor.models import AgentConfig, InterfaceMetric
from snmp_monitor.oid import IF_OPER_STATUS, INTERFACE_METRIC_COLUMNS
from snmp_monitor.snmp_client import snmp_walk


def _to_int(value, default: int = 0) -> int: 
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def poll_interfaces(agent: AgentConfig) -> list[InterfaceMetric]:
    """
    Legge la ifTable di un agente SNMP e costruisce una metrica per ogni interfaccia.
    """

    columns = {} # Metto i risultati delle walk

    for name, oid in INTERFACE_METRIC_COLUMNS.items(): # Esegue una walk per ogni colonna della tabella
        columns[name] = snmp_walk(
            agent.host,
            agent.port,
            agent.community,
            oid.value,
        )

    metriche = [] # Metriche per una interfaccia
    timestamp = datetime.now()
    interface_indexes = columns["ifDescr"].keys() # Prende gli indici delle interfacce usando ifDescr

    for if_index in interface_indexes: # Costruisco la riga InterfaceMetric per ogni interfaccia
        statusCode = _to_int(columns["ifOperStatus"].get(if_index)) 

        misura = InterfaceMetric(
            timestamp = timestamp,
            agent = agent.name,
            if_index = if_index,
            if_name = columns["ifDescr"].get(if_index, ""),
            if_status = IF_OPER_STATUS.get(statusCode, "unknown"),
            in_octets = _to_int(columns["ifInOctets"].get(if_index)),
            out_octets = _to_int(columns["ifOutOctets"].get(if_index)),
            in_errors = _to_int(columns["ifInErrors"].get(if_index)),
            out_errors = _to_int(columns["ifOutErrors"].get(if_index)),
        )
        metriche.append(misura)
        
    return metriche

def poller_mbps(agent: AgentConfig, interval: int = 5) -> list[InterfaceMetric]:
    """
    Esegue due polling a distanza di interval secondi e calcola la velocità in Mbps.
    """
    
    # I Mbps si può calcolare prendendo i valori di quanti byte sono entrati e usciti da una interfaccia di rete (che sono rispettivamente ifInOctets e ifOutOctets)
    # E applicando la formula: Mbps = ((octets_attuali - octets_precedenti) * 8) / secondi_trascorsi / 1_000_000
    
    octes_precedenti = poll_interfaces(agent)
    time.sleep(interval)
    octes_attuali = poll_interfaces(agent)
    
    # Trasformo le metriche che ho raccolto in un dizionario
    # Affinché per accedere subito ai valori di quell'interfaccia
    
    previous_by_index = {
        metrica.if_index: metrica
        for metrica in octes_precedenti
    }
    
    metriche = []
    
    for current in octes_attuali:
        previous = previous_by_index.get(current.if_index)
        
        if previous is None:
            metriche.append(current)
            continue
        
        # Calcolo il tempo trascorso fra le due letture
        delta_time = (current.timestamp - previous.timestamp).total_seconds()
        
        # Calcolo i byte ricevuti tra la prima e la seconda lettura
        delta_in = current.in_octets - previous.in_octets
        
        # Calcolo i byte inviati tra la prima e la seconda lettura
        delta_out = current.out_octets - previous.out_octets
        
        if delta_time <= 0 or delta_in < 0 or delta_out < 0:
            in_mbps = 0.0
            out_mbps = 0.0
        else:
            in_mbps = (delta_in * 8) / delta_time / 1_000_000
            out_mbps = (delta_out * 8) / delta_time / 1_000_000
        
        # Inserisco i valori calcolati nelle metriche
        misura = InterfaceMetric(
            timestamp=current.timestamp,
            agent=current.agent,
            if_index=current.if_index,
            if_name=current.if_name,
            if_status=current.if_status,
            in_octets=current.in_octets,
            out_octets=current.out_octets,
            in_errors=current.in_errors,
            out_errors=current.out_errors,
            in_mbps=round(in_mbps, 4),
            out_mbps=round(out_mbps, 4),
        )
        
        metriche.append(misura)
    
    return metriche