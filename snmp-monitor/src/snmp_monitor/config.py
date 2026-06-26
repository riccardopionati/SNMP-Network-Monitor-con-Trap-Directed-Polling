import yaml

from snmp_monitor.models import AgentConfig

def leggi_config(path: str) -> list[AgentConfig]:
    """
    Legge lil contenuto yaml del file di configurazione e restituisce una lista di oggetti AgentConfig.
    """

    with open(path, "r") as f:
        agent = yaml.safe_load(f)
    
    agents = []
    
    for agent in agent["agents"]:
        agent = AgentConfig(
            name = agent["name"],
            host = agent["host"],
            port = agent["port"],
            community = agent["community"]
        )
        agents.append(agent)
        
    return agents