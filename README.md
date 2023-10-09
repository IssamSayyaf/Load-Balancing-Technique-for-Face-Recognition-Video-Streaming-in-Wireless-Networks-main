# Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks
This project has been done in collaboration with Ahmad Mahmod

# Introduction
The ever-increasing demand for high-quality video streaming has posed significant challenges for wireless networks. With limited bandwidth and varying network conditions, ensuring a seamless streaming experience for users has become a complex task. Load balancing techniques play a crucial role in optimizing network resources, mitigating congestion, and delivering uninterrupted video playback. This report focuses on the implementation of load balancing technique specifically tailored for video streaming in wireless networks using Mininet WiFi and the RYU controller.
The rapid growth of video streaming services, coupled with the proliferation of wireless devices, has intensified the strain on wireless networks. Bandwidth limitations and fluctuating network conditions often result in suboptimal video quality, buffering, and playback interruptions. Therefore, an effective load balancing technique is necessary to distribute network traffic intelligently, optimize resource utilization, and improve the quality of video streaming in wireless networks.
The primary objectives of this project are as follows:
1. Develop and implement a load-balancing technique tailored for video streaming in wireless networks.
2. Utilize Mininet WiFi, an emulation platform, to create a realistic simulated environment for wireless network experiments.
3. Employ the RYU controller, a software-defined networking (SDN) controller, for centralized network management and control.
4. Enhance video streaming performance by dynamically adapting video quality levels, and balancing traffic load across network paths.
We evaluate the contribution of our load-balancing technique that measure the congestion and usage of paths for paths’ selection by compare the performance of the technique with the static paths mechanism, which depends on the hop counts.
Two tools, iperf and PSNR have characterized the performance. The former for general data connections and the latter for video quality.

# Network Configuration
In the simulation, we use Mininet-Wifi to simulate a wireless network with multiple Access Points APs that cover the Cosenza City area using SUMO simulator area supported by a backbone of wired switches. The users of the network are cars; create an ad-hoc scenario, which streams a video to a fixed server connected directly with the backbone. The APs and the backbone switches are OpenV Switches (OVSs) that are connected to a central SDN RYU controller.
The controller, through collect information about the links congestions and utilization in other routes, finds the optimal paths to achieve the load balancing.

# Network Topology 
The network Topology consists of nine APs connected to three central switches (each switch connect three APs) on Cosenza City roads
All links has the same capacity 10 Mbps from the APs to the switches.

<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/843e6782cd72e0b1d19345d7c69c6e69a69a4d43/Images/topology.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 1: The Topology</em>
</p>


<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/70fc76b03286448cfa24bd49c7670041c64c1976/Images/RYU%20topo.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 2: The RYU Topology</em>
</p>


<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/70fc76b03286448cfa24bd49c7670041c64c1976/Images/netx%20topo.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 3: The Networkx Topology</em>
</p>


<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/70fc76b03286448cfa24bd49c7670041c64c1976/Images/SUMO%20topo.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 4: The SUMO Topology</em>
</p>


<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/70fc76b03286448cfa24bd49c7670041c64c1976/Images/mininet%20topo.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 5: Mininet Topology</em>
</p>

# Results

<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/70fc76b03286448cfa24bd49c7670041c64c1976/Images/PSNR.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 6: PSNR</em>
</p>

<p align="center">
  <img src="https://github.com/ahmad2nawras/Load-Balancing-Technique-for-Face-Recognition-Video-Streaming-in-Wireless-Networks/blob/70fc76b03286448cfa24bd49c7670041c64c1976/Images/throughput.png" alt="alt text" width="width" height="height" />
  <br>
  <em>Figure 7: Throughout</em>
</p>

