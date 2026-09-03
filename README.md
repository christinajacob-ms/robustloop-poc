# RobustLoop - Proof of Concept

**Automated Reliability Testing for Physical AI.**

This repository contains a minimal Proof of Concept (PoC) for RobustLoop, a CI/CD pipeline tool designed to test how robotic systems react to **semantic sensor faults** before software is deployed to physical hardware.

## 🛑 The Problem
Most robotics testing focuses on normal operating conditions or statistical noise (e.g., Gaussian noise in Gazebo/Isaac Sim). However, the most dangerous and expensive field failures are caused by *semantically plausible* but fundamentally false data:
- A distance sensor freezing at `1.5m` while the robot continues moving.
- A timestamp mismatch causing delayed control loop reactions.
- Two sensors individually reporting plausible values that contradict each other.

In these cases, the robot's software blindly trusts the faulty input, often leading to collisions, damaged hardware, or unplanned production stops.

## 🚀 The PoC Concept
Instead of just simulating noise, this script demonstrates **deterministic fault injection combined with safety assertions**. 

It simulates a robot driving toward an obstacle. A fault injector intercepts the sensor data stream (simulating a ROS2 message structure). The system then checks a deterministic rule:

```python
# Safety Assertion Example
if true_dist <= brake_threshold_m and sensor_dist > brake_threshold_m:
    status = "FAIL: Collision imminent, sensor missed ground truth"

Updated to V3: Now supports Industrial-Grade faults including Jitter, Clock-Drift, Packet Loss, and Transient Outliers based on feedback from industry partners.
