import networkx as nx
from pox.core import core
from pox.openflow.discovery import Discovery
from pox.openflow.discovery import LinkEvent
from pox.openflow.libopenflow_01 import ofp_flow_mod, ofp_match, ofp_action_output


log = core.getLogger()

class TopologyExample(object):
    def __init__(self):
        # Register to listen for LinkEvents
        core.openflow_discovery.addListeners(self)
        core.openflow.addListeners(self)
        self.graph = nx.Graph()
        self.switches={}
        self.blocked_switches={}
        log.info("Topology initialized")

    def _handle_ConnectionDown(self, event):
        """
        Handle switch disconnection by removing it from self.switches and cleaning up topology.
        """
        dpid = event.dpid
        # Remove from self.switches
        if dpid in self.switches:
            del self.switches[dpid]
            log.info("Switch %s disconnected and removed from self.switches", dpid)
        # Remove from self.blocked_switches
        if dpid in self.blocked_switches:
            del self.blocked_switches[dpid]
            log.info("Switch %s removed from self.blocked_switches", dpid)
        # Remove from self.graph
        if dpid in self.graph:
            self.graph.remove_node(dpid)
            log.info("Switch %s removed from topology graph", dpid)
        self.log_switch_ports()

    def spt(self):
        switches = list(self.switches.keys())
        active_switches = [dpid for dpid in self.switches.keys() if self.is_switch_active(dpid)]
        root_switch = min(switches)
        while (root_switch not in active_switches):
            del self.switches[root_switch]
            switches = list(self.switches.keys())
            active_switches = [dpid for dpid in self.switches.keys() if self.is_switch_active(dpid)]
            root_switch = min(switches)
        
        for switch in self.switches:
            if (switch != root_switch):
                path, hops = self.bfs_hops(switch, root_switch)
                for port in self.switches[switch]:
                    if (path[1] not in self.switches[switch][port]):
                        connected = self.links.get((switch, port))
                        connected_dpid, connected_port = connected
                        self.block_port(switch, port)
 


    def _handle_LinkEvent(self, event):
        link = event.link
        if event.added:
            self.graph.add_edge(link.dpid1, link.dpid2)
            log.info("Link added: %s[%s] <--> %s[%s]",
                     link.dpid1, link.port1,
                     link.dpid2, link.port2)
        elif event.removed:
            self.graph.remove_edge(link.dpid1, link.dpid2)
            log.info("Link removed: %s[%s] <--> %s[%s]", link.dpid1, link.port1, link.dpid2, link.port2)
    
    def _handle_PortStatus(self, event):
        """
        Handle port status changes to update port information.
        """
        dpid = event.dpid
        port = event.ofp
        port_no = event.port_no
        reason = event.reason
        if reason == ofp_port_reason.OFPPR_ADD:
            if dpid not in self.switches:
                self.switches[dpid] = {}
            connected = self.links.get((dpid, port_no))
            connected_dpid, connected_port = connected
            self.switches[dpid][port_no] = connected_dpid
            log.info("Port %s added on switch %s", port_no, dpid)
        elif reason == ofp_port_reason.OFPPR_DELETE:
            connected = self.links.get((dpid, port_no))
            connected_dpid, connected_port = connected
            self.switches.get(dpid, {}).pop(port_no, None)
            self.switches.get(connected_dpid, {}).pop(connected_port, None)

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
            hops = len(path) - 1
            log.info("Path from %s to %s: %s (%s hops)", src, dst, path, hops)
            return path, hops
        except nx.NetworkXNoPath:
            log.warning("No path from %s to %s", src, dst)
            return [],-1

    
    def block_port(self, dpid, port_no):
        if dpid not in self.switches or port_no not in self.switches.get(dpid, {}):
            log.warning("Cannot block unknown port %s on switch %s", port_no, dpid)
            return
        msg = ofp_flow_mod()
        msg.priority = 65000  # High priority
        msg.match = ofp_match()
        msg.match.in_port = port_no
        msg.actions = []  # No actions = drop
        core.openflow.sendToDPID(dpid, msg)
        log.info("Installed drop rule on switch %s port %s", dpid, port_no)
        if dpid not in self.switches:
                self.blocked_switches[dpid] = {}
        connected = self.links.get((dpid, port_no))
        connected_dpid, connected_port = connected
        self.blocked_switches[dpid][port_no] = connected_dpid
        log.info("Port %s added on switch %s", port_no, dpid)
    
    def unblock_port(self, dpid, port_no):
        if dpid not in self.switches or port_no not in self.switches.get(dpid, {}):
            log.warning("Cannot unblock unknown port %s on switch %s", port_no, dpid)
            return
        msg = ofp_flow_mod()
        msg.command = ofp_flow_mod.OFPFC_DELETE  # Delete matching flows
        msg.match = ofp_match()
        msg.match.in_port = port_no
        core.openflow.sendToDPID(dpid, msg)
        log.info("Unblocked port %s on switch %s", port_no, dpid)
        self.switches.get(dpid, {}).pop(port_no, None)
        log.info("Port %s removed from switch %s", port_no, dpid)

    def _handle_ConnectionUp(self, event):
        dpid = event.dpid
        self.switches[dpid] = {}
        # Get initial ports from switch features
        for port in event.ofp.ports:
            port_no = port.port_no
            if port_no <= ofp_port_no.OFPP_MAX and not port.config & ofp_port_config.OFPPC_PORT_DOWN:
                self.switches[dpid][port_no] = "unknown"
        log.info("Switch %s connected with ports: %s", dpid, list(self.switches[dpid].keys()))
        self.log_switch_ports()

def launch():
    if not core.running:
        log.warning("POX core not running, deferring registration")
        return
    core.registerNew(TopologyExample)
    def spt():

