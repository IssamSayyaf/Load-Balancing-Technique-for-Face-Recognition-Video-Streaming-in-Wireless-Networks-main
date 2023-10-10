'''
DEVELOPER: Mohamad Issam Sayyaf
EMAIL: issamsayyaf97@gmail.com
'''
from http import server
from math import inf
from multiprocessing import Process
#from xmlrpc.client import _HostType
import time
import requests
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv6
from ryu.lib.packet import ether_types
from ryu.topology import event
from threading import Thread, Lock
from multiprocessing import Process
import requests
import json
import networkx as nx
import matplotlib.pyplot as plt
import pickle




class ProjectController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectController, self).__init__(*args, **kwargs)
        self.net = nx.Graph()
        # datapath_list, key=switch ID, value= switch object
        self.datapath_list = {}
        # arp_table, key = ip, value= MAC
        self.arp_table = {}
        # switches: switches dpid
        self.switches = []
        # hosts IPs
        self.hosts = []
        # hosts MACs
        self.hosts_mac = []
        # Graph links
        self.links = []
        # Host-Switch connection, key = hostIP::switchID, value = port Number
        self.hostSwitch = {}
        # Switch-Switch connection, key = switchID::switchID, value = port Number::port Number.
        self.switchSwitch = {}
        # The Path Computation Time for each path
        self.pathTime = []
        # Average TIme of path computation (sec)
        self.pathAvgTime = 0

        self.metric = 3

        self.lock = Lock()

        self.process = Thread(target=self.start_routing)
        self.process.start()

        self.threads = []
        self.serverIP = '10.0.0.101'
        self.used_links = {}
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        # print "Adding flow ", match, actions
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # Extract the msg details
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # avoid broadcast from LLDP
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Drop the IPV6 Packets.
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None

        dst = eth.dst
        src = eth.src

        # Add the packet for first tim. Otherwise, follow the flows
        if src not in self.hosts_mac:
            self.hosts_mac.append(src)
        else:
            return

        # Flood to all ports (For the First time)
        out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    # When a new switch joins
    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        switch = ev.switch.dp
        ofp_parser = switch.ofproto_parser
        id = str(switch.id)
        print('New Switch Added, ID: ', id)
        if id not in self.switches:
            self.switches.append(id)
            self.datapath_list[id] = switch

            # Request port/link descriptions, useful for obtaining bandwidth
            req = ofp_parser.OFPPortDescStatsRequest(switch)
            switch.send_msg(req)

    @set_ev_cls(event.EventSwitchLeave, MAIN_DISPATCHER)
    def switch_leave_handler(self, ev):
        switch = str(ev.switch.dp.id)
        if switch in self.switches:
            self.switches.remove(switch)
            del self.datapath_list[switch]
            # del self.adjacency[str(switch)]
            self.update_graph()

    @set_ev_cls(event.EventLinkAdd, MAIN_DISPATCHER)
    def link_add_handler(self, ev):
        s1 = ev.link.src
        s2 = ev.link.dst
        s1_dpid = str(s1.dpid)
        s1_port = str(s1.port_no)
        s2_dpid = str(s2.dpid)
        s2_port = str(s2.port_no)

        # Add the link between switches and the connected ports
        self.switchSwitch[s1_dpid + '::' + s2_dpid] = s1_port + '::' + s2_port
        self.switchSwitch[s2_dpid + '::' + s1_dpid] = s2_port + '::' + s1_port

        # Add the new link to the virtualized network
        self.links.append((str(s1.dpid), str(s2.dpid)))
        self.update_graph()


    @set_ev_cls(event.EventLinkDelete, MAIN_DISPATCHER)
    def link_delete_handler(self, ev):
        s1 = ev.link.src
        s2 = ev.link.dst
        # Exception handling if switch already deleted
        # Delete the link from the virtualized network
        try:
            self.links.remove((str(s1.dpid), str(s2.dpid)))
            self.update_graph()
        except KeyError:
            pass

    # Add the new host to the hosts list and the link to the switch
    @set_ev_cls(event.EventHostAdd, MAIN_DISPATCHER)
    def host_add_handler(self, ev):

        msg = ev.host.to_dict()
        host_ip = str(''.join(msg['ipv4']))
        if host_ip == None or host_ip == '':
            return
        with self.lock:
            self.hosts.append(host_ip)
        print('New Host Added', host_ip, self.hosts)
        host_dpid = str(msg['port']['dpid'].strip('0'))
        host_port = str(msg['port']['port_no'].strip('0'))
        if host_ip == '':
            return
        # Host-switch port
        key = str(host_ip) + '::' + str(host_dpid)
        self.hostSwitch[key] = host_port

        # Add to the existing hosts
        if host_ip not in self.hosts:
            
            self.hosts.append(host_ip)

        # Add the link between the host and switch then update the virtualized network
        link = (host_ip, host_dpid)
        if link not in self.links:
            self.links.append(link)
            self.update_graph()
            self.find_paths(host_ip)
        #self.plot()

    # HOST
    # {'mac': '00:00:00:00:00:05', 'ipv4': ['192.168.1.5'], 'ipv6': [],
    #  'port': {'dpid': '0000000000000004', 'port_no': '00000004', 'hw_addr': '4e:e8:18:fe:34:f1', 'name': 's4-eth4'}}

    @set_ev_cls(event.EventHostDelete, MAIN_DISPATCHER)
    def host_leave_handler(self, ev):
        msg = ev.host.to_dict()
        host_ip = str(''.join(msg['ipv4']))
        host_dpid = str(msg['port']['dpid'].strip('0'))
        self.links.remove((host_ip, host_dpid))
        self.update_graph()
        self.find_paths(host_ip)


    # Find all available paths between src and dst
    def get_paths(self, src, dst):
        # All available paths between src and dst
        paths = nx.all_simple_paths(self.net, src, dst)
        l=[]
        for p in paths:
            l.append(p)
        return l

    # Find Dijkstra pathe between src and dst
    def get_dijkstra_path(self, src, dst):
        # Return the Dijkstra best path
        path = nx.dijkstra_path(self.net, src, dst, weight='weight')
        return path

    # Update the graph with the new links/nodes
    def update_graph(self):
        # Build new graph with the new links/nodes
        self.net = nx.Graph()
        #self.net.add_nodes_from(self.switches)
        #self.net.add_nodes_from(self.hosts)
        self.net.add_edges_from(self.links)
        print(self.net)
        with open("net.pkl", "wb") as file:
                pickle.dump(self.net, file)        

    # Plot the virtualized network
    def plot(self):
        pos = nx.spring_layout(self.net)
        nx.draw_networkx_nodes(self.net, pos, )
        nx.draw_networkx_labels(self.net, pos)
        nx.draw_networkx_edges(self.net, pos)
        nx.draw_networkx_edges(self.net, pos)
        plt.show()
            

    # Add new flow to the proper switch
    def new_flow(self, src, dst, path):
        print("Installed Path: ", path)
        # If the hosts connected to the same switch
        if len(path) < 4:
            inport = self.hostSwitch[src + '::' + path[1]]
            outport = self.hostSwitch[dst + '::' + path[1]]
            dpid = int(path[1])
            # IPV4 flow
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                    "match": {"ipv4_src": src, "eth_type": 2048, "ipv4_dst": dst},
                    "actions": [{"type": "OUTPUT", "port": outport}]}
            self.systemCommand(body)

            # ARP flow
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "priority": 11111,
                    "match": {"eth_type": 2054, "arp_spa": src, "arp_tpa": dst},
                    "actions": [{"port": outport, "type": "OUTPUT"}]}
            self.systemCommand(body)

            # IPV4 flow (Reverse Path)
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                    "match": {"ipv4_src": dst, "eth_type": 2048, "ipv4_dst": src},
                    "actions": [{"type": "OUTPUT", "port": inport}]}
            self.systemCommand(body)

            # ARP flow (Reverse Path)
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                    "match": {"eth_type": 2054, "arp_spa": dst, "arp_tpa": src},
                    "actions": [{"port": inport, "type": "OUTPUT"}]}
            self.systemCommand(body)
            return "Ok"
        
        for node in range(1, len(path) - 2):
            if node == 1:
                inport = self.hostSwitch[src + '::' + path[node]]
                outport = self.switchSwitch[path[node] + '::' + path[node + 1]].split('::')[0]
            else:
                inport = self.switchSwitch[path[node - 1] + '::' + path[node]].split('::')[1]
                outport = self.switchSwitch[path[node] + '::' + path[node + 1]].split('::')[0]
            dpid = int(path[node])

            # IPV4 flow
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                    "match": {"ipv4_src": src, "eth_type": 2048, "ipv4_dst": dst},
                    "actions": [{"type": "OUTPUT", "port": outport}]}
            self.systemCommand(body)

            # ARP flow
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "priority": 11111,
                    "match": {"eth_type": 2054, "arp_spa": src, "arp_tpa": dst},
                    "actions": [{"port": outport, "type": "OUTPUT"}]}
            self.systemCommand(body)

            # IPV4 flow (Reverse Path)
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                    "match": {"ipv4_src": dst, "eth_type": 2048, "ipv4_dst": src},
                    "actions": [{"type": "OUTPUT", "port": inport}]}
            self.systemCommand(body)

            # ARP flow (Reverse Path)
            body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                    "match": {"eth_type": 2054, "arp_spa": dst, "arp_tpa": src},
                    "actions": [{"port": inport, "type": "OUTPUT"}]}
            self.systemCommand(body)

        # The flows of the last switch in the path
        dpid = int(path[-2])
        inport = self.switchSwitch[path[-3] + '::' + path[-2]].split('::')[1]
        outport = self.hostSwitch[dst + '::' + path[-2]]

        # IPV4 flow
        body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                "match": {"ipv4_src": src, "eth_type": 2048, "ipv4_dst": dst},
                "actions": [{"type": "OUTPUT",
                             "port": outport}]}
        self.systemCommand(body)

        # ARP flow
        body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                "match": {"eth_type": 2054, "arp_spa": src, "arp_tpa": dst},
                "actions": [{"port": outport, "type": "OUTPUT"}]}
        self.systemCommand(body)

        # IPV4 flow (Reverse Path)
        body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                "match": {"ipv4_src": dst, "eth_type": 2048, "ipv4_dst": src},
                "actions": [{"type": "OUTPUT", "port": inport}]}
        self.systemCommand(body)

        # ARP flow (Reverse Path)
        body = {"dpid": dpid, "cookie": 1, "cookie_mask": 1, "table_id": 0, "priority": 11111,
                "match": {"eth_type": 2054, "arp_spa": dst, "arp_tpa": src},
                "actions": [{"port": inport, "type": "OUTPUT"}]}
        self.systemCommand(body)
        return "Ok"

    # Send the new flow
    def systemCommand(self, body, ):
        url = "http://localhost:8080/stats/flowentry/add"
        headers = {'Content-type': 'application/json'}
        r = requests.post(url, data=json.dumps(body), headers=headers)
        print("\n*** Flow Pushed\n")

    def get_hosts(self):
        return self.hosts
    
    def start_routing(self):
        while True:
            self.threads = []
            self.used_links = {}
            for host1 in self.get_hosts():
                #served_clients.append(host1)
                if host1==self.serverIP:
                    continue
                self.find_paths(host_ip=host1)
                '''th = Thread(target=self.find_paths, args=(host1,))
                self.threads.append(th)'''
            print("Threads: ", self.threads, "Hosts: ", self.get_hosts())
            
            '''for th1 in self.threads:
                print(th1)
                th1.start()
                time.sleep(1)'''

            time.sleep(3)
    
    # Retrive link's cost
    def observe_cost(self,url,srcSwitch):
        response = requests.get(url)
        cost=0
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Extract the JSON data from the response
            json_data = response.json()
            # Extract tx_bytes from the JSON data
            tx_bytes = int(json_data[str(srcSwitch)][0]['tx_bytes'])
            # Extract tx_bytes from the JSON data
            rx_bytes = int(json_data[str(srcSwitch)][0]['rx_bytes'])
            cost = tx_bytes + rx_bytes

        else:
            print("Error: Request failed with status code", response.status_code)
            cost = inf
        return cost
    
    # Get the link cost
    def get_link_cost(self, srcSwitch, dstSwitch):
        # Get the link cost between two switches
        # The URL to retrieve the JSON response
        srcDst = str(srcSwitch)+"::"+str(dstSwitch)

        # very high cost
        if srcDst in self.used_links.keys():
            cost = self.used_links[srcDst] * 100
            print("Cost of ", srcDst, " is: ", str(cost), "\n\n\n\n")
            print("USE: ", srcDst,"\n\n\n\n")
        
        else:
            ports = self.switchSwitch[str(srcSwitch)+'::'+str(dstSwitch)]
            port = int(ports.split('::')[0])
            url = "http://localhost:8080/stats/port/"+str(srcSwitch)+"/"+str(port)
            # Send GET request to the URL
            cost1 = self.observe_cost(url,srcSwitch,)
            time.sleep(1)
            cost2 = self.observe_cost(url, srcSwitch,)
            cost = cost2 - cost1
            with self.lock:
                self.used_links[srcDst] = cost
            print("\n\n\n\n",srcDst, " has been added", "\n\n\n\n")
            
        return cost
    
    # Find all paths weighted with the cost
    def find_paths(self, host_ip):
        for host in self.hosts:
            if host != host_ip and host==self.serverIP:
                start_time = time.time()
                paths = self.get_paths(host_ip, host)   
                # All paths
                for path in paths:
                    path_cost = 0
                    # All links
                    for node in range(1, len(path) - 2):
                        s = path[node]
                        d = path[node + 1]
                        cost = self.get_link_cost(s, d)
                        path_cost += cost
                        self.net[s][d]['weight'] = cost
                    # Get the best Dijkstra Path
                    print('Cost pf the path: ',path, " is: ", path_cost)
                best_path = self.get_dijkstra_path(host_ip, host)

                for i in range(len(best_path)-1):
                    srcDst = str(best_path[i])+"::"+str(best_path[i+1])
                    self.used_links[srcDst] = path_cost
                
                self.new_flow(host_ip, host, best_path)
                path_time = time.time() - start_time
                print('Path from ', host_ip, 'to', host, ': ', best_path)
                self.pathTime.append(path_time)
