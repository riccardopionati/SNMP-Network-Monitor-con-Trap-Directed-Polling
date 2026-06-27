# Questo file esegue richieste SNMP (GET e WALK)

from pysnmp.hlapi.asyncio import bulkCmd, SnmpEngine, CommunityData, UdpTransportTarget, ObjectType, ObjectIdentity



def snmp_walk(host:str, port:int, community:str, oid:str):
    """
    Esegue una richiesta SNMP WALK verso l'agente specificato.
    """
    
    risultati = {}
    
    for errorIndication, errorStatus, errorIndex, varBinds in bulkCmd(
        SnmpEngine(), # Gestisce il ciclo di vita del pacchetto
        CommunityData(community, mpModel = 1), # Descrive il tipo di operazione da fare in questo caso GETBULK (con mpModel = 1)
        UdpTransportTarget(("127.0.0.1", 1161)), # Specifico dove si trova l'agent
        0,
        25, # Numero massimo di ripetizioni che voglio ricevere da GETBULK
        ObjectType(ObjectIdentity(oid)), # Rappresenta l'OID che voglio leggere
        lexicographicMode = False # Dice alla WALK di fermarsi quando esce dal sottoalbero
    ):
        
        if errorIndication: # Errori di comunicazione (timeout, agent non raggiungibile ecc.)
            raise RuntimeError(errorIndication)
        
        if errorStatus: # Errore restituito dall'agente (OID inesistente ecc.)
            raise RuntimeError(errorStatus)

        # varBinds contiene la risposta restituita dall'agent con questa struttura: (OID_risposto, valore)
        for oidResponse, value in varBinds:
            oidResponse = str(oidResponse)
            
            if not oidResponse.startswith(oid + "."):
                continue
        
            idx = int(oidResponse.removeprefix(oid + "."))
            risultati[idx] = value.prettyPrint() # Salvo il valore nel dizionario
    
    return risultati