#!/usr/bin/env python3
"""Team 11 topology. Switch ports are intentionally created in documented order."""
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI


class PacketLossTopo(Topo):
    def build(self):
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        # A root-namespace management host gives h2 a reachable dedicated UDP
        # telemetry endpoint; it does not carry application DATA traffic.
        ctrl = self.addHost('ctrl', ip='10.0.0.254/24', mac='00:00:00:00:00:fe',
                            inNamespace=False)
        s1 = self.addSwitch('s1', dpid='0000000000000001', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', dpid='0000000000000002', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', dpid='0000000000000003', protocols='OpenFlow13')
        # Keep this exact link order: it defines the port map in controller.py.
        self.addLink(h1, s1)                                  # s1-eth1
        self.addLink(h2, s2)                                  # s2-eth1
        self.addLink(s1, s2, cls=TCLink, delay='5ms')         # s1-eth2 / s2-eth2 primary
        self.addLink(s1, s3, cls=TCLink, delay='10ms')        # s1-eth3 / s3-eth1
        self.addLink(s3, s2, cls=TCLink, delay='10ms')        # s3-eth2 / s2-eth3 alternate
        self.addLink(ctrl, s1)                                # s1-eth4 telemetry endpoint


def main():
    net = Mininet(topo=PacketLossTopo(), controller=None, switch=OVSSwitch,
                  link=TCLink, autoSetMacs=False, autoStaticArp=False)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    try:
        net.start()
        h1, h2 = net.get('h1'), net.get('h2')
        ctrl = net.get('ctrl')
        h1.cmd('ip neigh replace 10.0.0.2 lladdr 00:00:00:00:00:02 dev h1-eth0')
        h1.cmd('ip neigh replace 10.0.0.254 lladdr 00:00:00:00:00:fe dev h1-eth0')
        h2.cmd('ip neigh replace 10.0.0.1 lladdr 00:00:00:00:00:01 dev h2-eth0')
        h2.cmd('ip neigh replace 10.0.0.254 lladdr 00:00:00:00:00:fe dev h2-eth0')
        # ctrl is in the root namespace; install static neighbors there too.
        ctrl.cmd('ip neigh replace 10.0.0.1 lladdr 00:00:00:00:00:01 dev ctrl-eth0')
        ctrl.cmd('ip neigh replace 10.0.0.2 lladdr 00:00:00:00:00:02 dev ctrl-eth0')
        print('\n=== TEAM 11 PACKET LOSS TOPOLOGY ===')
        print('Primary DATA path:   h1 -- s1(port 1->2) -- s2(port 2->1) -- h2')
        print('Alternate DATA path: h1 -- s1(port 1->3) -- s3(port 1->2) -- s2(port 3->1) -- h2')
        print('Telemetry path:      h2 -- s2(port 1->3) -- s3(port 2->1) -- s1(port 3->4) -- ctrl')
        print('Controller: 127.0.0.1:6653 | Telemetry: 10.0.0.254:6000')
        print('At mininet> run: pingall')
        CLI(net)
    finally:
        net.stop()

if __name__ == '__main__':
    main()
