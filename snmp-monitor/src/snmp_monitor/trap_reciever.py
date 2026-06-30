# Ricevitore SNMP Trap del progetto SNMP Monitor.
# Il modulo resta in ascolto su una porta UDP, riceve trap SNMPv2c,
# riconosce il tipo di evento ricevuto e lo registra in un file CSV.
#
# In questa prima versione il modulo NON fa polling immediato:
# riceve, interpreta, stampa e salva le trap.

from __future__ import annotations

import csv
import threading
from datetime import datetime
from pathlib import Path

from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

from snmp_monitor.models import TrapEvent



#OID standard usato nelle trap SNMPv2c per indicare il tipo di trap.
#Es:
#1.3.6.1.6.3.1.1.5.3 = linkDown
#1.3.6.1.6.3.1.1.5.4 = linkUp
SNMP_TRAP_OID = "1.3.6.1.6.3.1.1.4.1.0"

#mappa degli OID standard delle trap SNMP più comuni.
#serve per salvare un nome leggibile invece del solo OID numerico.
TRAP_TYPES = {
    "1.3.6.1.6.3.1.1.5.1": "coldStart",
    "1.3.6.1.6.3.1.1.5.2": "warmStart",
    "1.3.6.1.6.3.1.1.5.3": "linkDown",
    "1.3.6.1.6.3.1.1.5.4": "linkUp",
    "1.3.6.1.6.3.1.1.5.5": "authenticationFailure",
}

# __file__ punta a:
#snmp-monitor/src/snmp_monitor/trap_reciver.py
#parents[2] risale a:
#snmp-monitor/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAPS_CSV = PROJECT_ROOT / "traps.csv"

def _to_string(value) -> str:
    
    #Converto un valore PySNMP/ASN.1 in stringa leggibile.
    #PySNMP rappresenta OID e valori SNMP con oggetti propri.
    #prettyPrint(), quando disponibile, restituisce una forma più chiara.

    if hasattr(value, "prettyPrint"):
        return value.prettyPrint()

    return str(value)


def _get_trap_type(varbinds: dict[str, str]) -> str:
    
    #ricavo il tipo di trap dai varbind ricevuti.
    #Nelle trap SNMPv2c il tipo della trap si trova normalmente
    #nel varbind con OID:
    #1.3.6.1.6.3.1.1.4.1.0
    #Se il valore è uno degli OID standard, restituisco un nome leggibile.
    #Altrimenti restituisco direttamente l'OID ricevuto.
    
    trap_oid = varbinds.get(SNMP_TRAP_OID, "unknown")

    return TRAP_TYPES.get(trap_oid, trap_oid)

def _get_source_ip(snmp_engine, state_reference) -> str:
    
    #Recupero l'indirizzo IP sorgente della trap.
    #state_reference è un riferimento interno fornito da PySNMP.
    #Da questo riferimento proviamo a ricavare l'indirizzo del mittente.
    #Se il recupero fallisce, restituisco 'unknown' per non bloccare il receiver.

    try:
        transport_domain, transport_address = (
            snmp_engine.msg_and_pdu_dsp.get_transport_info(state_reference)
        )

        # Di norma transport_address è una tupla:
        #   ("127.0.0.1", porta_sorgente)
        if isinstance(transport_address, tuple):
            return str(transport_address[0])

        return str(transport_address)

    except Exception:
        return "unknown"
    
def _salva_trap_csv(trap: TrapEvent) -> None:
    
    #Salva una trap nel file traps.csv.
    #Il file viene creato automaticamente se non esiste.

    file_esiste = TRAPS_CSV.exists()

    with TRAPS_CSV.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        #Se il file non esiste ancora, scrivo l'intestazione.
        if not file_esiste:
            writer.writerow([
                "timestamp",
                "source_ip",
                "trap_type",
                "varbinds",
            ])

        writer.writerow([
            trap.timestamp.isoformat(),
            trap.source_ip,
            trap.trap_type,
            trap.varbinds,
        ])

def _callback_trap(snmp_engine, state_reference, context_engine_id, context_name, var_binds, cb_ctx,):

    #Callback chiamata automaticamente da PySNMP quando arriva una trap.
    #Passaggi:
    #1.recupera IP sorgente;
    #2.converte i varbind in un dizionario leggibile;
    #3.riconosce il tipo di trap;
    #4.crea un oggetto TrapEvent;
    #5.salva la trap in CSV;
    #6.stampa la trap a video.

    #ip del dispositivo che ha inviato il trap
    source_ip = _get_source_ip(snmp_engine, state_reference)

    #conversione dei varbin in dizionario:
    #lo trasformo {"OID" : val}
    varbinds_dict: dict[str, str] = {}

    for oid, value in var_binds:
        oid_str = _to_string(oid)
        value_str = _to_string(value)

        varbinds_dict[oid_str] = value_str

    #riconoscimento del tipo di trap
    trap_type = _get_trap_type(varbinds_dict)

    #creo l'oggetto trap event
    trap = TrapEvent(
        timestamp=datetime.now(),
        source_ip=source_ip,
        trap_type=trap_type,
        varbinds=varbinds_dict,
    )

    #salvo trap sul csv
    _salva_trap_csv(trap)

    print(f"\n[TRAP] Ricevuta trap da {source_ip}")
    print(f"[TRAP] Tipo trap: {trap_type}")

    for oid, value in varbinds_dict.items():
        print(f"[TRAP]   {oid} = {value}")

def avvia_trap_receiver(host: str = "127.0.0.1", port: int = 9162, community: str = "public") -> None:

    #Avvia il receiver SNMP Trap.
    #Parametri:
    #- host: indirizzo IP locale su cui ascoltare;
    #- port: porta UDP di ascolto;
    #- community: community SNMPv1/v2c accettata.

    #uso la porta 9162 invece della porta standard 162 perché
    #la 162 è una porta privilegiata e può richiedere permessi amministrativi.

    #motore principale, gestisce ricezione, decodifica e dispatch dei messaggi SNMP.
    snmp_engine = engine.SnmpEngine()

    #Configurazione del trasporto UDP.
    #Qui dico al receiver di ascoltare su host:port.
    config.add_transport(
        snmp_engine,
        udp.DOMAIN_NAME,
        udp.UdpTransport().open_server_mode((host, port)),
    )

    #Configurazione della community SNMPv1/v2c accettata.
    config.add_v1_system(
        snmp_engine,
        "trap-area",
        community,
    )

    #Registrazione della callback.
    #Quando arriva una trap, PySNMP esegue _callback_trap().
    ntfrcv.NotificationReceiver(
        snmp_engine,
        _callback_trap,
    )

    print(f"[TRAP] Receiver avviato su udp://{host}:{port} community={community}")
    print("[TRAP] In attesa di trap SNMP...")

    try:
        #Mantiene attivo il dispatcher.
        snmp_engine.transport_dispatcher.job_started(1)

        #Avvia il ciclo di ascolto.
        #Questa chiamata è bloccante: il processo resta in ascolto.
        snmp_engine.open_dispatcher()

    except KeyboardInterrupt:
        print("\n[TRAP] Receiver arrestato manualmente.")

    finally:
        #Chiusura ordinata del dispatcher SNMP.
        snmp_engine.close_dispatcher()


def avvia_in_background(host: str = "127.0.0.1", port: int = 9162, community: str = "public") -> threading.Thread:
    
    #Avvia il trap receiver in un thread separato.
    #Questa funzione serve quando il trap receiver deve essere usato
    #insieme al resto del programma.

    #Motivo:
    #avvia_trap_receiver() è una funzione bloccante, perché resta
    #sempre in ascolto delle trap SNMP.

    #Se la chiamassimo direttamente da main.py, il programma resterebbe
    #fermo sul receiver e non continuerebbe con il polling periodico.

    #- il receiver parte in background;
    #- il programma principale resta libero;
    #- il polling può continuare a funzionare.

    #creo un thread separato che eseguirà avvia_trap_receiver().

    thread = threading.Thread(
        target=avvia_trap_receiver, #funz che il thread deve eseguire
        kwargs={
            "host": host,
            "port": port,
            "community": community,
        }, #parametri per la funz target
        daemon=True, #se true significa che il thread non impedisce la chiusura del progrm.
        name="snmp-trap-receiver",
    )

    # Avvio effettivo del thread.
    thread.start()

    return thread


#Esecuzione diretta del modulo per test standalone.
#
#Da lanciare dalla cartella snmp-monitor con:
#   python -m snmp_monitor.trap_reciever
if __name__ == "__main__":
    avvia_trap_receiver()
    
