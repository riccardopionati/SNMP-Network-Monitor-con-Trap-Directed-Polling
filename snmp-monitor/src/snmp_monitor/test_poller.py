from snmp_monitor.models import AgentConfig
from snmp_monitor.poller import poller_mbps

agent = AgentConfig(
    name="localhost",
    host="127.0.0.1",
    port=161,
    community="public",
)

metriche = poller_mbps(agent, interval=5)

for metrica in metriche:
    print(metrica)