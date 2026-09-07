# Real-Time NILM Inference Pipeline (STM32F469)

A real-time Non-Intrusive Load Monitoring (NILM) pipeline that disaggregates 
total household power consumption into individual appliance-level estimates, 
running inference on an STM32F469I-DISCO board.

## Overview

The pipeline collects aggregate power measurements from an STM32MP157F-DK2 
board (via the MCP39F511A power-monitoring IC), streams them over HTTP to a 
desktop bridge script, and forwards the processed samples over UART to an 
STM32F469I-DISCO board for real-time appliance-level inference using a 
lightweight LSTM model converted with X-CUBE-AI.

## Pipeline stages

1. **Data acquisition** — The MCP39F511A measures instantaneous power on the 
   STM32MP15 (Cortex-A7), which exposes readings over HTTP.
2. **Desktop bridge** — `mcp-totale-serial-bridge.py` polls the HTTP endpoint 
   every 5 seconds, validates and logs each sample, and buffers unsent 
   samples in SQLite to guarantee delivery across transient link failures.
3. **UART transmission** — Validated samples are sent to the STM32F469 over 
   UART via the ST-Link USB interface, using a fixed 65-byte packet format 
   (magic number, sequence number, 14 float features, checksum).
4. **On-device validation** — The STM32F469 checks the magic number and 
   checksum before accepting a packet, discarding malformed or corrupted data.
5. **Feature normalization** — Aggregate power is standardized (mean/std), 
   while 13 time- and statistics-derived features are min-max scaled, 
   matching the preprocessing used during training.
6. **Inference** — A retrained, resource-constrained LSTM model (converted 
   from the original BiLSTM, which X-CUBE-AI couldn't convert due to 
   unsupported dynamic control flow) estimates per-appliance power draw and 
   ON/OFF state directly on the Cortex-M4.
7. **Output** — Estimated appliance states and power values are displayed 
   live on the board's LCD.

## Wireless variant

An ESP32-based bridge (MQTT over Wi-Fi, HiveMQ public broker) is also 
supported as an alternative to the wired ST-Link/UART link, decoupling the 
STM32F469 from a desktop connection.

## Hardware

- STM32MP157F-DK2 (data acquisition, Cortex-A7 + Cortex-M4)
- STM32F469I-DISCO (real-time inference, Cortex-M4, 180 MHz, 2 MB Flash / 384 KB SRAM)
- MCP39F511A power-monitoring IC
- ESP32 (optional Wi-Fi bridge)

## Software

- STM32CubeIDE / X-CUBE-AI (stedgeai) for model conversion and firmware
- Python (desktop bridge, HTTP polling, SQLite buffering, UART transmission)
<img width="1391" height="738" alt="validation" src="https://github.com/user-attachments/assets/c462898b-2ca8-4533-8182-521b946848ea" />
