import asyncio
import logging
from datetime import datetime
from dataclasses import replace

from snmp_monitor.models import AgentConfig, InterfaceMetric
from snmp_monitor.oid import IF_OPER_STATUS, INTERFACE_METRIC_COLUMNS
from snmp_monitor.snmp_client import snmp_bulk_walk

# COUNTER32 è un tipo di dato definito in SNMP senza segno e SOLO positivo. Rappresenta il numero di byte che attraversa un'interfaccia
COUNTER32_MAX = 4_294_967_295

# Logger per il modulo
logger = logging.getLogger(__name__)



def _to_int(value, default: int = 0) -> int:
    """ 
    Converte in interi i valori letti da una WALK
    """
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
    
 
def counter32_delta(current: int, previous: int) -> int:
    """
    Calcola la differenza tra due letture di un Counter32 gestendo
    correttamente il rollover (wrap-around a 2^32).
    """
    delta = current - previous
    if delta < 0:
        # Counter rollover: il contatore ha raggiunto COUNTER32_MAX e si è azzerato
        delta = (COUNTER32_MAX - previous) + current + 1
    return delta


async def poll_interface(agent: AgentConfig) -> list[InterfaceMetric]:
    """
    Legge la ifTable di un agente SNMP e costruisce una metrica per ogni interfaccia.
    """
    
    risultati = await asyncio.gather(
        *[
            snmp_bulk_walk(agent.host, agent.port, agent.community, oid.value)
            for oid in INTERFACE_METRIC_COLUMNS.values()
        ]
    )

    # Unisce i risultati delle metriche ottenute alle interfacce
    columns: dict[str, dict[int, str]] = dict(
        zip(INTERFACE_METRIC_COLUMNS.keys(), risultati)
    )

    interface_indexes = columns["ifDescr"].keys()

    timestamp = datetime.now()
    metriche: list[InterfaceMetric] = []

    for if_index in interface_indexes:
        status_code = _to_int(columns["ifOperStatus"].get(if_index))

        metriche.append(
            InterfaceMetric(
                timestamp=timestamp,
                agent=agent.name,
                if_index=if_index,
                if_name=columns["ifDescr"].get(if_index, ""),
                if_status=IF_OPER_STATUS.get(status_code, "unknown"),
                in_octets=_to_int(columns["ifInOctets"].get(if_index)),
                out_octets=_to_int(columns["ifOutOctets"].get(if_index)),
                in_errors=_to_int(columns["ifInErrors"].get(if_index)),
                out_errors=_to_int(columns["ifOutErrors"].get(if_index)),
                # in_mbps e out_mbps restano None: calcolati da compute_delta()
                # al prossimo ciclo, quando esiste una lettura precedente
            )
        )

    return metriche


def compute_mbps(current: InterfaceMetric, previous: InterfaceMetric) -> InterfaceMetric:
    """
    Calcola in_mbps e out_mbps per differenza tra due letture consecutive.
    Ritorna una nuova InterfaceMetric con i campi Mbps valorizzati.
    """
    
    delta_time = (current.timestamp - previous.timestamp).total_seconds()

    if delta_time <= 0:
        logger.warning(
            "[%s] if%d: delta_time=%f non valido, skip calcolo Mbps",
            current.agent, current.if_index, delta_time
        )
        return current  # ritorna senza modificare in_mbps / out_mbps

    delta_in = counter32_delta(current.in_octets, previous.in_octets)
    delta_out = counter32_delta(current.out_octets, previous.out_octets)

    in_mbps = round((delta_in * 8) / delta_time / 1_000_000, 4)
    out_mbps = round((delta_out * 8) / delta_time / 1_000_000, 4)

    return replace(current, in_mbps=in_mbps, out_mbps=out_mbps)


async def poll_all_agents(agents: list[AgentConfig]) -> list[InterfaceMetric]:
    """
    Esegue il polling di tutti gli agenti in parallelo con asyncio.gather().
    Lo stato precedente (_previous) viene aggiornato dopo ogni ciclo.

    Flusso per ogni agente:
      1. poll_agent(): legge i contatori
      2. poller_mbps() calcola Mbps rispetto alla lettura precedente
      3. aggiorna _previous per il ciclo successivo
    """
    
    # Chiama parallelamente poll_agent su tutti gli agenti
    results_per_agent = await asyncio.gather(
        *[poll_interface(agent) for agent in agents],
        return_exceptions = True,
    )
    
    
    all_metrics: list[InterfaceMetric] = []

    # Associa per ogni agente le sue metriche 
    for agent, result in zip(agents, results_per_agent):
        # Se si verifica un errore passa a quello successivo
        if isinstance(result, Exception):
            logger.error("[%s] Polling fallito: %s", agent.name, result)
            continue

        # Raccolgo le metriche precedenti per calolare il traffico
        agent_previous = previous.get(agent.name, {})
        # Qui dentro ci vanno le liste con i Mbps aggiornati
        metriche_con_delta: list[InterfaceMetric] = []

        # Scorre tutte le interfacce
        for current in result:
            previous = agent_previous.get(current.if_index) # Prende la lettura precendete
            if previous is not None:
                current = compute_mbps(current, previous) # Qui calcola il traffico
            metriche_con_delta.append(current)

        # Aggiorna lo storico per il prossimo ciclo
        previous[agent.name] = {m.if_index: m for m in result}
    
        all_metrics.extend(metriche_con_delta)

    return all_metrics