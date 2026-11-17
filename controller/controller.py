"""OS-Ken OpenFlow 1.3 controller with UDP telemetry-triggered path switching."""
import json
import os
import socket
import time
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib import hub
from controller.telemetry_validation import validate_telemetry

H1 = "10.0.0.1"
H2 = "10.0.0.2"
CTRL_IP = "10.0.0.254"
TELEMETRY_PORT = int(os.getenv("TEAM11_TELEMETRY_PORT", "6000"))
RECEIVER_IP = os.getenv("TEAM11_RECEIVER_IP", H2)
RECEIVER_PORT = int(os.getenv("TEAM11_RECEIVER_PORT", "5001"))
LOSS_TRIGGER = float(os.getenv("TEAM11_LOSS_TRIGGER", "10"))
RECOVERY_THRESHOLD = float(os.getenv("TEAM11_RECOVERY_THRESHOLD", "2"))
TRIGGER_SAMPLES = int(os.getenv("TEAM11_TRIGGER_SAMPLES", "2"))
HOLD_DOWN = float(os.getenv("TEAM11_HOLD_DOWN", "5"))
MAX_AGE = float(os.getenv("TEAM11_TELEMETRY_MAX_AGE", "10"))

# DPID: [(input port, output port, IPv4 source, IPv4 destination)]
PRIMARY = {
    1: [(1, 2, H1, H2), (2, 1, H2, H1)],
    2: [(2, 1, H1, H2), (1, 2, H2, H1)],
    3: [],
}
ALTERNATE = {
    1: [(1, 3, H1, H2), (3, 1, H2, H1)],
    2: [(3, 1, H1, H2), (1, 3, H2, H1)],
    3: [(1, 2, H1, H2), (2, 1, H2, H1)],
}


class PacketLossController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PacketLossController, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.active_path = "PRIMARY"
        self.high_samples = 0
        self.recovery_since = None
        self.last_report = {}
        self.last_seen_seq = 0
        self.path_change_time = None
        self.path_change_seq = 0
        self.telemetry_greenlet = hub.spawn(self.telemetry_loop)
        self.logger.info("Team11 controller started: OF1.3 telemetry=%s:%s receiver=%s:%s",
                         "0.0.0.0", TELEMETRY_PORT, RECEIVER_IP, RECEIVER_PORT)

    def add_flow(self, dp, priority, match, actions, cookie=0x11):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, cookie=cookie, priority=priority,
                                match=match, instructions=inst)
        dp.send_msg(mod)

    def delete_cookie(self, dp, cookie):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        mod = parser.OFPFlowMod(datapath=dp, cookie=cookie,
                                cookie_mask=0xffffffffffffffff,
                                table_id=ofp.OFPTT_ALL, command=ofp.OFPFC_DELETE,
                                out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                                match=parser.OFPMatch())
        dp.send_msg(mod)

    def install_route(self, dp):
        dpid = dp.id
        parser, ofp = dp.ofproto_parser, dp.ofproto
        self.delete_cookie(dp, 0x11)
        self.delete_cookie(dp, 0x33)
        table = PRIMARY if self.active_path == "PRIMARY" else ALTERNATE
        for in_port, out_port, src, dst in table.get(dpid, []):
            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                    ipv4_src=src, ipv4_dst=dst)
            self.add_flow(dp, 100, match, [parser.OFPActionOutput(out_port)])
        # Keep the receiver's telemetry path on the alternate links so it survives
        # impairment or failure of the primary s1-s2 link. Port mapping: s2: h2=1,s1=2,s3=3;
        # s3: s1=1,s2=2; s1: h1=1,s2=2,s3=3,ctrl=4.
        telemetry_routes = {
            2: (1, 3),  # h2 -> s3
            3: (2, 1),  # s2 -> s1
            1: (3, 4),  # s3 -> controller host
        }
        if dpid in telemetry_routes:
            in_port, out_port = telemetry_routes[dpid]
            # Generic h2<->controller management path (also supports pingall).
            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                    ipv4_src=H2, ipv4_dst=CTRL_IP)
            self.add_flow(dp, 50, match, [parser.OFPActionOutput(out_port)], cookie=0x33)
            match = parser.OFPMatch(in_port=telemetry_routes[dpid][1], eth_type=0x0800,
                                    ipv4_src=CTRL_IP, ipv4_dst=H2)
            reverse_out = {2: 1, 3: 2, 1: 3}[dpid]
            self.add_flow(dp, 50, match, [parser.OFPActionOutput(reverse_out)], cookie=0x33)
        # h1 <-> controller endpoint is directly connected to s1 port 4.
        if dpid == 1:
            self.add_flow(dp, 50, parser.OFPMatch(in_port=1, eth_type=0x0800,
                            ipv4_src=H1, ipv4_dst=CTRL_IP),
                          [parser.OFPActionOutput(4)], cookie=0x33)
            self.add_flow(dp, 50, parser.OFPMatch(in_port=4, eth_type=0x0800,
                            ipv4_src=CTRL_IP, ipv4_dst=H1),
                          [parser.OFPActionOutput(1)], cookie=0x33)
        # A high-priority dedicated telemetry match is logged separately by UDP port.
        if dpid in telemetry_routes:
            in_port, out_port = telemetry_routes[dpid]
            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                    ip_proto=17, ipv4_src=H2, ipv4_dst=CTRL_IP,
                                    udp_dst=TELEMETRY_PORT)
            self.add_flow(dp, 200, match, [parser.OFPActionOutput(out_port)], cookie=0x22)
        self.logger.info("Installed %s path rules on s%s", self.active_path, dpid)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.logger.info("OpenFlow switch connected: dpid=%s", dp.id)
        self.install_route(dp)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(dp.id, None)

    def change_path(self, new_path, reason):
        if self.active_path == new_path:
            return
        old = self.active_path
        trigger_time = time.time()
        self.active_path = new_path
        if new_path == "ALTERNATE":
            self.path_change_time = trigger_time
            self.path_change_seq = self.last_seen_seq
        else:
            self.path_change_time = None
        for dp in list(self.datapaths.values()):
            self.install_route(dp)
        self.logger.warning("PATH CHANGE %s -> %s reason=%s timestamp=%.3f",
                            old, new_path, reason, trigger_time)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def primary_port_status(self, ev):
        dp = ev.msg.datapath
        dpid = dp.id
        port_no = ev.msg.desc.port_no
        ofp = dp.ofproto
        # The s1-s2 primary link is s1 port 2 and s2 port 2.
        if dpid in (1, 2) and port_no == 2:
            down = bool(ev.msg.desc.state & ofp.OFPPS_LINK_DOWN)
            if down:
                self.logger.error("PRIMARY LINK DOWN reported by s%s port %s", dpid, port_no)
                self.change_path("ALTERNATE", f"primary link down at s{dpid} port {port_no}")
            else:
                self.logger.info("PRIMARY LINK UP reported by s%s port %s", dpid, port_no)

    def validate_telemetry(self, msg, addr):
        return validate_telemetry(msg, addr, (RECEIVER_IP, RECEIVER_PORT),
                                  MAX_AGE, self.last_report)

    def process_telemetry(self, raw, addr):
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.logger.warning("TELEMETRY REJECTED from %s: malformed JSON", addr)
            return
        valid, reason = self.validate_telemetry(msg, addr)
        if not valid:
            self.logger.warning("TELEMETRY REJECTED from %s: %s", addr, reason)
            return
        self.last_report[msg["stream_id"]] = (msg["report_id"], float(msg["timestamp"]))
        loss = float(msg["loss_pct"])
        last_seq = msg["last_received_seq"]
        self.logger.info("TELEMETRY accepted stream=%s report=%s expected=%s received=%s loss=%.2f%% last_seq=%s active=%s",
                         msg["stream_id"], msg["report_id"], msg["window_expected"],
                         msg["window_received"], loss, last_seq, self.active_path)
        if (self.active_path == "ALTERNATE" and self.path_change_time is not None
                and last_seq > self.path_change_seq):
            elapsed = time.time() - self.path_change_time
            self.logger.warning("DELIVERY CONFIRMED after path change: seq=%s recovery_time=%.3fs",
                                last_seq, elapsed)
            self.path_change_time = None
        self.last_seen_seq = max(self.last_seen_seq, last_seq)
        if self.active_path == "PRIMARY":
            self.recovery_since = None
            self.high_samples = self.high_samples + 1 if loss >= LOSS_TRIGGER else 0
            if self.high_samples >= TRIGGER_SAMPLES:
                self.change_path("ALTERNATE", f"loss {loss:.1f}% >= {LOSS_TRIGGER:.1f}% for {TRIGGER_SAMPLES} reports")
                self.high_samples = 0
        else:
            if loss <= RECOVERY_THRESHOLD:
                if self.recovery_since is None:
                    self.recovery_since = time.monotonic()
                elif time.monotonic() - self.recovery_since >= HOLD_DOWN:
                    self.change_path("PRIMARY", f"loss <= {RECOVERY_THRESHOLD:.1f}% for {HOLD_DOWN:.1f}s")
                    self.recovery_since = None
                    self.high_samples = 0
            else:
                self.recovery_since = None

    def telemetry_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", TELEMETRY_PORT))
        sock.settimeout(1.0)
        self.logger.info("Telemetry UDP listener bound to 0.0.0.0:%s", TELEMETRY_PORT)
        while True:
            try:
                raw, addr = sock.recvfrom(8192)
                self.process_telemetry(raw, addr)
            except socket.timeout:
                continue
            except Exception as exc:
                self.logger.exception("Telemetry processing error: %s", exc)
