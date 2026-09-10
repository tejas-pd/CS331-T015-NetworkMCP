# Live lab demo

1. Use two isolated Ubuntu lab machines. Record interface names with `ip a`.
2. Run `iperf3 -s` on the target host and `iperf3 -c TARGET` from the test host to establish an unshaped baseline.
3. Set `NETWORK_ASSISTANT_EXECUTE=1` and apply a 5 Mbps rule using the interface that carries the shaped egress traffic.
4. Show `sudo tc class show dev INTERFACE` and repeat the `iperf3` test. Capture both results.
5. Demonstrate `block 192.168.1.1`: it must be rejected by policy. Demonstrate a permitted test address only when you have a recovery path.

`tc` direction matters: the included rule matches packet source on outbound traffic. Inbound traffic needs shaping through an IFB device, which is deliberately outside this first safe demo.
