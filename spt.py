import networkx as nx
from pox.core import core
from pox.openflow.discovery import Discovery, LinkEvent
from pox.openflow.discovery import LinkEvent
from pox.openflow.libopenflow_01 import ofp_flow_mod, ofp_match, ofp_action_output
from collections import deque

log = core.getLogger()

class TopologyExample(object):
    def __init__(self):
        # Register to listen for LinkEvents
        core.openflow_discovery.addListeners(self)
        log.info("TopologyExample initialized and listening for LinkEvents")
        self.graph = nx.Graph()
        log.info("HopCounter initialized")

    def _handle_LinkEvent(self, event):
        link = event.link
        if event.added:
            self.graph.add_edge(link.dpid1, link.dpid2)
            log.info("Link added: %s[%s] <--> %s[%s]",
                     link.dpid1, link.port1,
                     link.dpid2, link.port2)
        elif event.removed: 
            if self.graph.has_edge(link.dpid1, link.dpid2):
                self.graph.remove_edge(link.dpid1, link.dpid2)

                log.info("Link removed: %s[%s] <--> %s[%s]",
                        link.dpid1, link.port1,
                        link.dpid2, link.port2)
    
    def _handle_PortStatus(self, event):
        """
        Handle port status changes to update port information.
        """
        dpid = event.dpid
        port_no = event.port_no
        if event.added:
            if dpid not in self.switches:
                self.switches[dpid] = {}
            self.switches[dpid][port_no] = "unknown"
            log.info("Port %s added on switch %s", port_no, dpid)
        elif event.deleted:
            self.switches.get(dpid, {}).pop(port_no, None)
            log.info("Port %s removed from switch %s", port_no, dpid)
        self.log_switch_ports()

    def log_switch_ports(self):
        """
        Log the current switch-to-port mappings.
        """
        log.info("Current switch-port mappings:")
        for dpid, ports in self.switches.items():
            port_list = [f"port {p}: {d}" for p, d in ports.items()]
            log.info("Switch %s: %s", dpid, ", ".join(port_list))

    def bfs_hops(self, src, dst):
        try:
            path = nx.shortest_path(self.graph, src, dst)
            return len(path) - 1  # Number of hops
        except nx.NetworkXNoPath:
            log.warning("No path from %s to %s", src, dst)
            return -1

    
    def block_port(self, dpid, port_no):
        msg = ofp_flow_mod()
        msg.priority = 65000  # High priority
        msg.match = ofp_match()
        msg.match.in_port = port_no
        msg.actions = []  # No actions = drop
        core.openflow.sendToDPID(dpid, msg)
        log.info("Installed drop rule on switch %s port %s", dpid, port_no)
        self.switches.get(dpid, {}).pop(port_no, None)
        log.info("Port %s removed from switch %s", port_no, dpid)
    
    def unblock_port(self, dpid, port_no):
        msg = ofp_flow_mod()
        msg.command = ofp_flow_mod.OFPFC_DELETE  # Delete matching flows
        msg.match = ofp_match()
        msg.match.in_port = port_no
        core.openflow.sendToDPID(dpid, msg)
        log.info("Unblocked port %s on switch %s", port_no, dpid)
        if dpid not in self.switches:
                self.switches[dpid] = {}
        self.switches[dpid][port_no] = "unknown"
        log.info("Port %s added on switch %s", port_no, dpid)

def launch():
    core.registerNew(TopologyExample)
