# Data sources, hashes and environment

## Traffic
CIC-IDS2017 packet captures from the Canadian Institute for Cybersecurity (University of New Brunswick), each verified against the official MD5 file.

| File | SHA-256 |
| --- | --- |
| Monday-WorkingHours.pcap | f6eac599358f216b074338813a1cf7be3cc4e91d116e13efc0dc71f2cca11972 |
| Tuesday-WorkingHours.pcap | 080c2250154c5a174c03660ed0f75a3858d41a27511ba716e780d7bcb1ec4c57 |
| Wednesday-workingHours.pcap | cd2674db7559a53f24bc03be3239b315700174ccaef72d10f5edc4c1a08f6186 |
| Thursday-WorkingHours.pcap | 38f8b1bb276849bf1721f7c4de22bebfa7f59a74e52286d4c0a37edbb118fe01 |
| Friday-WorkingHours.pcap | beff0dcce1eebc9b2454582f4dc8ed0ba0112b2c619a710bf03af93147254cd0 |

## Labels
Corrected flow labels of Liu, Engelen, Lynar, Essam and Joosen, "Error Prevalence in NIDS datasets: A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018", IEEE CNS 2022 (`CICIDS2017_improved.zip`, downloaded 21 Oct 2026 from the authors' site).

## Ruleset
Emerging Threats Open for Suricata 7.0.3, snapshot of 19 Oct 2026, 53,150 enabled rules, SHA-256 6c051c4c137058938bea64524207addf7049cc76109f8f8397f0b0edc886569b. The snapshot is included in the Zenodo archive, because a fresh download will differ.

## Base configuration
Ubuntu default `suricata.yaml` modified by `harness/prepare_base.py` (HOME_NET = 192.168.10.0/24, alerts and stats only); SHA-256 of the result 1286e2fd84bb8535bed1d69e1dedf006585e96aa58fe8a58099774f176d67d55.

## Environment
Ubuntu 24.04 VM (VirtualBox, 4 vCPU, 7.8 GiB) on an AMD Ryzen 7 7735HS laptop; Suricata 7.0.3 (Ubuntu package), offline mode, `--runmode single`, pinned to one vCPU; Python 3.12.3.
