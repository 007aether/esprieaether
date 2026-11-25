#!/usr/bin/env python3
"""
Multi-GPU Resource Planner for Colibri
Supports tensor parallelism, pipeline parallelism, and expert parallelism
for distributed MoE model inference.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from enum import Enum


class ParallelismStrategy(Enum):
    TENSOR_PARALLEL = "tensor_parallel"
    PIPELINE_PARALLEL = "pipeline_parallel"
    EXPERT_PARALLEL = "expert_parallel"
    DATA_PARALLEL = "data_parallel"
    HYBRID = "hybrid"


class GPUVendor(Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"  # Metal


@dataclass
class GPUDevice:
    """Represents a single GPU device"""
    index: int
    name: str
    vendor: GPUVendor
    vram_total_mb: int
    vram_free_mb: int
    compute_capability: Optional[str] = None  # e.g., "8.6" for RTX 3080
    pcie_bandwidth_gb_s: float = 16.0  # PCIe 4.0 x16
    nvlink_bandwidth_gb_s: float = 0.0  # NVLink if available
    tensor_cores: bool = False
    driver_version: str = ""


@dataclass
class ModelRequirements:
    """Model resource requirements"""
    dense_params_mb: int
    expert_params_mb: int
    num_experts: int
    experts_per_token: int
    num_layers: int
    hidden_size: int
    num_attention_heads: int
    kv_heads: int
    head_dim: int
    context_length: int
    dtype: str = "fp16"  # fp16, bf16, fp8, int4
    quantization: Optional[str] = None


@dataclass
class PlacementPlan:
    """Execution placement plan"""
    strategy: ParallelismStrategy
    num_gpus: int
    gpu_indices: List[int]
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    expert_parallel_size: int = 1
    data_parallel_size: int = 1
    layers_per_gpu: List[int] = field(default_factory=list)
    experts_per_gpu: List[int] = field(default_factory=list)
    estimated_vram_per_gpu_mb: List[int] = field(default_factory=list)
    estimated_latency_ms: float = 0.0
    estimated_throughput_tok_s: float = 0.0
    communication_overhead_ms: float = 0.0


class MultiGPUPlanner:
    """
    Plans optimal multi-GPU placement for MoE models.
    Considers VRAM, compute, communication bandwidth, and parallelism strategies.
    """

    def __init__(self, devices: List[GPUDevice]):
        self.devices = devices
        self._sort_devices()

    def _sort_devices(self):
        """Sort devices by VRAM (descending)"""
        self.devices.sort(key=lambda d: d.vram_free_mb, reverse=True)

    def get_available_devices(self, min_vram_mb: int = 0) -> List[GPUDevice]:
        """Get devices with sufficient VRAM"""
        return [d for d in self.devices if d.vram_free_mb >= min_vram_mb]

    def plan_placement(
        self,
        model: ModelRequirements,
        strategy: ParallelismStrategy = ParallelismStrategy.HYBRID,
        max_gpus: Optional[int] = None,
    ) -> List[PlacementPlan]:
        """Generate placement plans for a model"""

        available = self.get_available_devices()
        if not available:
            return []

        max_gpus = max_gpus or len(available)
        available = available[:max_gpus]

        plans = []

        if strategy in (ParallelismStrategy.TENSOR_PARALLEL, ParallelismStrategy.HYBRID):
            plans.extend(self._plan_tensor_parallel(model, available))

        if strategy in (ParallelismStrategy.PIPELINE_PARALLEL, ParallelismStrategy.HYBRID):
            plans.extend(self._plan_pipeline_parallel(model, available))

        if strategy in (ParallelismStrategy.EXPERT_PARALLEL, ParallelismStrategy.HYBRID):
            plans.extend(self._plan_expert_parallel(model, available))

        if strategy in (ParallelismStrategy.DATA_PARALLEL, ParallelismStrategy.HYBRID):
            plans.extend(self._plan_data_parallel(model, available))

        if strategy == ParallelismStrategy.HYBRID:
            plans.extend(self._plan_hybrid(model, available))

        # Sort by estimated performance
        plans.sort(key=lambda p: p.estimated_throughput_tok_s, reverse=True)
        return plans

    def _plan_tensor_parallel(
        self,
        model: ModelRequirements,
        devices: List[GPUDevice],
    ) -> List[PlacementPlan]:
        """Plan tensor parallel placement"""
        plans = []

        # Tensor parallel splits attention heads and MLP across GPUs
        # Requires: num_heads % tp_size == 0, hidden_size % tp_size == 0

        for tp_size in [2, 4, 8]:
            if tp_size > len(devices):
                continue
            if model.num_attention_heads % tp_size != 0:
                continue
            if model.hidden_size % tp_size != 0:
                continue

            selected = devices[:tp_size]
            min_vram = min(d.vram_free_mb for d in selected)

            # Estimate VRAM per GPU
            # Dense params split by tp_size
            dense_per_gpu = model.dense_params_mb / tp_size
            # Expert params replicated (each GPU has full experts for its shard)
            expert_per_gpu = model.expert_params_mb
            # KV cache
            kv_per_gpu = self._estimate_kv_cache(model, tp_size)
            # Activation memory
            act_per_gpu = self._estimate_activations(model, tp_size)

            total_per_gpu = dense_per_gpu + expert_per_gpu + kv_per_gpu + act_per_gpu
            total_per_gpu *= 1.2  # 20% overhead

            if total_per_gpu > min_vram:
                continue

            # Estimate performance
            latency = self._estimate_tp_latency(model, tp_size, selected)
            throughput = self._estimate_tp_throughput(model, tp_size, selected)
            comm = self._estimate_tp_communication(model, tp_size, selected)

            plans.append(PlacementPlan(
                strategy=ParallelismStrategy.TENSOR_PARALLEL,
                num_gpus=tp_size,
                gpu_indices=[d.index for d in selected],
                tensor_parallel_size=tp_size,
                estimated_vram_per_gpu_mb=[int(total_per_gpu)] * tp_size,
                estimated_latency_ms=latency,
                estimated_throughput_tok_s=throughput,
                communication_overhead_ms=comm,
            ))

        return plans

    def _plan_pipeline_parallel(
        self,
        model: ModelRequirements,
        devices: List[GPUDevice],
    ) -> List[PlacementPlan]:
        """Plan pipeline parallel placement"""
        plans = []

        for pp_size in [2, 4, 8]:
            if pp_size > len(devices):
                continue
            if model.num_layers % pp_size != 0:
                continue

            layers_per_stage = model.num_layers // pp_size
            selected = devices[:pp_size]

            plans_per_stage = []
            for i in range(pp_size):
                stage_layers = layers_per_stage
                # First and last stages have embeddings
                dense_mb = model.dense_params_mb / pp_size
                if i == 0 or i == pp_size - 1:
                    dense_mb += 100  # embeddings

                expert_mb = model.expert_params_mb  # Each stage has full experts
                kv_mb = self._estimate_kv_cache(model, 1) * stage_layers / model.num_layers
                act_mb = self._estimate_activations(model, 1) * stage_layers / model.num_layers

                total = (dense_mb + expert_mb + kv_mb + act_mb) * 1.2
                plans_per_stage.append(int(total))

            min_vram = min(d.vram_free_mb for d in selected)
            if max(plans_per_stage) > min_vram:
                continue

            latency = self._estimate_pp_latency(model, pp_size, selected)
            throughput = self._estimate_pp_throughput(model, pp_size, selected)
            comm = self._estimate_pp_communication(model, pp_size, selected)

            plans.append(PlacementPlan(
                strategy=ParallelismStrategy.PIPELINE_PARALLEL,
                num_gpus=pp_size,
                gpu_indices=[d.index for d in selected],
                pipeline_parallel_size=pp_size,
                layers_per_gpu=[layers_per_stage] * pp_size,
                estimated_vram_per_gpu_mb=plans_per_stage,
                estimated_latency_ms=latency,
                estimated_throughput_tok_s=throughput,
                communication_overhead_ms=comm,
            ))

        return plans

    def _plan_expert_parallel(
        self,
        model: ModelRequirements,
        devices: List[GPUDevice],
    ) -> List[PlacementPlan]:
        """Plan expert parallel placement (for MoE models)"""
        plans = []

        # Expert parallel distributes experts across GPUs
        # Each GPU holds a subset of experts for all layers
        num_experts = model.num_experts

        for ep_size in [2, 4, 8, 16]:
            if ep_size > len(devices):
                continue
            if num_experts % ep_size != 0:
                continue

            experts_per_gpu = num_experts // ep_size
            selected = devices[:ep_size]
            min_vram = min(d.vram_free_mb for d in selected)

            # Dense params replicated
            dense_per_gpu = model.dense_params_mb
            # Expert params split
            expert_per_gpu = model.expert_params_mb / ep_size
            # KV cache (full context on each)
            kv_per_gpu = self._estimate_kv_cache(model, 1)
            # Activations
            act_per_gpu = self._estimate_activations(model, 1)

            total_per_gpu = (dense_per_gpu + expert_per_gpu + kv_per_gpu + act_per_gpu) * 1.2

            if total_per_gpu > min_vram:
                continue

            latency = self._estimate_ep_latency(model, ep_size, selected)
            throughput = self._estimate_ep_throughput(model, ep_size, selected)
            comm = self._estimate_ep_communication(model, ep_size, selected)

            plans.append(PlacementPlan(
                strategy=ParallelismStrategy.EXPERT_PARALLEL,
                num_gpus=ep_size,
                gpu_indices=[d.index for d in selected],
                expert_parallel_size=ep_size,
                experts_per_gpu=[experts_per_gpu] * ep_size,
                estimated_vram_per_gpu_mb=[int(total_per_gpu)] * ep_size,
                estimated_latency_ms=latency,
                estimated_throughput_tok_s=throughput,
                communication_overhead_ms=comm,
            ))

        return plans

    def _plan_data_parallel(
        self,
        model: ModelRequirements,
        devices: List[GPUDevice],
    ) -> List[PlacementPlan]:
        """Plan data parallel placement (replicate model, split batch)"""
        plans = []

        for dp_size in [2, 4, 8]:
            if dp_size > len(devices):
                continue

            selected = devices[:dp_size]
            min_vram = min(d.vram_free_mb for d in selected)

            # Full model on each GPU
            dense = model.dense_params_mb
            expert = model.expert_params_mb
            kv = self._estimate_kv_cache(model, 1)
            act = self._estimate_activations(model, 1)

            total = (dense + expert + kv + act) * 1.2

            if total > min_vram:
                continue

            # Data parallel scales throughput linearly (ideally)
            base_latency = self._estimate_single_gpu_latency(model, selected[0])
            base_throughput = self._estimate_single_gpu_throughput(model, selected[0])

            plans.append(PlacementPlan(
                strategy=ParallelismStrategy.DATA_PARALLEL,
                num_gpus=dp_size,
                gpu_indices=[d.index for d in selected],
                data_parallel_size=dp_size,
                estimated_vram_per_gpu_mb=[int(total)] * dp_size,
                estimated_latency_ms=base_latency,
                estimated_throughput_tok_s=base_throughput * dp_size * 0.9,  # 90% scaling efficiency
                communication_overhead_ms=0,  # Gradient sync only
            ))

        return plans

    def _plan_hybrid(
        self,
        model: ModelRequirements,
        devices: List[GPUDevice],
    ) -> List[PlacementPlan]:
        """Plan hybrid parallelism (TP + PP + EP combinations)"""
        plans = []

        # Try TP=2, PP=2, EP=2 combinations
        for tp_size in [1, 2, 4]:
            for pp_size in [1, 2, 4]:
                for ep_size in [1, 2, 4]:
                    total_gpus = tp_size * pp_size * ep_size
                    if total_gpus > len(devices) or total_gpus < 2:
                        continue

                    # Validate divisibility
                    if tp_size > 1 and model.num_attention_heads % tp_size != 0:
                        continue
                    if tp_size > 1 and model.hidden_size % tp_size != 0:
                        continue
                    if pp_size > 1 and model.num_layers % pp_size != 0:
                        continue
                    if ep_size > 1 and model.num_experts % ep_size != 0:
                        continue

                    selected = devices[:total_gpus]
                    min_vram = min(d.vram_free_mb for d in selected)

                    # Calculate VRAM per GPU
                    dense_per = model.dense_params_mb / tp_size
                    expert_per = model.expert_params_mb / ep_size
                    kv_per = self._estimate_kv_cache(model, tp_size) * (model.num_layers / pp_size / model.num_layers)
                    act_per = self._estimate_activations(model, tp_size) * (model.num_layers / pp_size / model.num_layers)

                    total_per = (dense_per + expert_per + kv_per + act_per) * 1.2

                    if total_per > min_vram:
                        continue

                    latency = self._estimate_hybrid_latency(model, tp_size, pp_size, ep_size, selected)
                    throughput = self._estimate_hybrid_throughput(model, tp_size, pp_size, ep_size, selected)
                    comm = self._estimate_hybrid_communication(model, tp_size, pp_size, ep_size, selected)

                    plans.append(PlacementPlan(
                        strategy=ParallelismStrategy.HYBRID,
                        num_gpus=total_gpus,
                        gpu_indices=[d.index for d in selected],
                        tensor_parallel_size=tp_size,
                        pipeline_parallel_size=pp_size,
                        expert_parallel_size=ep_size,
                        layers_per_gpu=[model.num_layers // pp_size] * pp_size,
                        experts_per_gpu=[model.num_experts // ep_size] * ep_size,
                        estimated_vram_per_gpu_mb=[int(total_per)] * total_gpus,
                        estimated_latency_ms=latency,
                        estimated_throughput_tok_s=throughput,
                        communication_overhead_ms=comm,
                    ))

        return plans

    # ── Estimation Helpers ──────────────────────────────────────────────

    def _estimate_kv_cache(self, model: ModelRequirements, tp_size: int) -> int:
        """Estimate KV cache size in MB"""
        # KV cache = 2 * layers * context * kv_heads * head_dim * bytes_per_param
        bytes_per_param = {"fp16": 2, "bf16": 2, "fp8": 1, "int4": 0.5}.get(model.dtype, 2)
        kv_heads_per_gpu = model.kv_heads // tp_size
        kv_size = 2 * model.num_layers * model.context_length * kv_heads_per_gpu * model.head_dim * bytes_per_param
        return kv_size // (1024 * 1024)

    def _estimate_activations(self, model: ModelRequirements, tp_size: int) -> int:
        """Estimate activation memory in MB"""
        bytes_per_param = {"fp16": 2, "bf16": 2, "fp8": 1, "int4": 0.5}.get(model.dtype, 2)
        hidden_per_gpu = model.hidden_size // tp_size
        # Rough estimate: batch * seq * hidden * layers * 4 bytes
        act_size = 1 * model.context_length * hidden_per_gpu * model.num_layers * 4 * bytes_per_param
        return act_size // (1024 * 1024)

    def _estimate_single_gpu_latency(self, model: ModelRequirements, device: GPUDevice) -> float:
        """Estimate latency on single GPU"""
        # Simplified: based on FLOPS
        tflops = self._get_device_tflops(device)
        # MoE FLOPS per token ~ 6 * active_params
        active_params = model.dense_params_mb + model.expert_params_mb * model.experts_per_token / model.num_experts
        active_params *= 1e6  # to params
        flops_per_token = 6 * active_params
        latency_s = flops_per_token / (tflops * 1e12)
        return latency_s * 1000  # ms

    def _estimate_single_gpu_throughput(self, model: ModelRequirements, device: GPUDevice) -> float:
        """Estimate throughput on single GPU"""
        latency = self._estimate_single_gpu_latency(model, device)
        return 1000 / latency if latency > 0 else 0

    def _get_device_tflops(self, device: GPUDevice) -> float:
        """Get device TFLOPS (FP16/BF16 tensor core)"""
        # Rough estimates based on known GPUs
        name_lower = device.name.lower()
        if "h100" in name_lower:
            return 1979  # FP16 tensor core TFLOPS
        elif "a100" in name_lower:
            return 312
        elif "rtx 4090" in name_lower:
            return 82.6
        elif "rtx 3090" in name_lower:
            return 35.6
        elif "v100" in name_lower:
            return 125
        elif "t4" in name_lower:
            return 65
        elif "a10g" in name_lower:
            return 125
        else:
            # Estimate from VRAM
            return device.vram_total_mb / 1024 * 10  # Very rough

    def _estimate_tp_latency(self, model, tp_size, devices) -> float:
        base = self._estimate_single_gpu_latency(model, devices[0])
        # TP reduces compute but adds communication
        return base / tp_size * 1.1  # 10% communication overhead

    def _estimate_tp_throughput(self, model, tp_size, devices) -> float:
        base = self._estimate_single_gpu_throughput(model, devices[0])
        return base * tp_size * 0.9  # 90% scaling efficiency

    def _estimate_tp_communication(self, model, tp_size, devices) -> float:
        # All-reduce for attention output and MLP
        hidden = model.hidden_size
        bytes_per = {"fp16": 2, "bf16": 2}.get(model.dtype, 2)
        data_mb = 2 * hidden * bytes_per * model.num_layers / (1024 * 1024)
        # Bandwidth
        bw = devices[0].nvlink_bandwidth_gb_s or devices[0].pcie_bandwidth_gb_s
        return (data_mb / bw) * 1000 * 2  # ms, factor 2 for bidirectional

    def _estimate_pp_latency(self, model, pp_size, devices) -> float:
        base = self._estimate_single_gpu_latency(model, devices[0])
        # PP has pipeline bubbles
        return base * (1 + 1 / pp_size)  # Simplified bubble overhead

    def _estimate_pp_throughput(self, model, pp_size, devices) -> float:
        base = self._estimate_single_gpu_throughput(model, devices[0])
        return base * pp_size * 0.85  # 85% efficiency due to bubbles

    def _estimate_pp_communication(self, model, pp_size, devices) -> float:
        # Point-to-point between stages
        hidden = model.hidden_size
        bytes_per = {"fp16": 2, "bf16": 2}.get(model.dtype, 2)
        data_mb = hidden * model.context_length * bytes_per / (1024 * 1024)
        bw = devices[0].nvlink_bandwidth_gb_s or devices[0].pcie_bandwidth_gb_s
        return (data_mb / bw) * 1000 * pp_size

    def _estimate_ep_latency(self, model, ep_size, devices) -> float:
        base = self._estimate_single_gpu_latency(model, devices[0])
        # EP adds router computation and expert dispatch
        return base * 1.05

    def _estimate_ep_throughput(self, model, ep_size, devices) -> float:
        base = self._estimate_single_gpu_throughput(model, devices[0])
        return base * ep_size * 0.95  # 95% efficiency

    def _estimate_ep_communication(self, model, ep_size, devices) -> float:
        # All-to-all for expert dispatch
        hidden = model.hidden_size
        bytes_per = {"fp16": 2, "bf16": 2}.get(model.dtype, 2)
        tokens_per_expert = model.context_length * model.experts_per_token / ep_size
        data_mb = tokens_per_expert * hidden * bytes_per / (1024 * 1024)
        bw = devices[0].nvlink_bandwidth_gb_s or devices[0].pcie_bandwidth_gb_s
        return (data_mb / bw) * 1000 * ep_size

    def _estimate_hybrid_latency(self, model, tp, pp, ep, devices) -> float:
        base = self._estimate_single_gpu_latency(model, devices[0])
        compute_reduction = tp * ep
        pp_overhead = 1 + 1 / pp
        comm_overhead = 1.1
        return base * pp_overhead * comm_overhead / compute_reduction

    def _estimate_hybrid_throughput(self, model, tp, pp, ep, devices) -> float:
        base = self._estimate_single_gpu_throughput(model, devices[0])
        return base * tp * pp * ep * 0.8

    def _estimate_hybrid_communication(self, model, tp, pp, ep, devices) -> float:
        # Sum of all communication patterns
        tp_comm = self._estimate_tp_communication(model, tp, devices) if tp > 1 else 0
        pp_comm = self._estimate_pp_communication(model, pp, devices) if pp > 1 else 0
        ep_comm = self._estimate_ep_communication(model, ep, devices) if ep > 1 else 0
        return tp_comm + pp_comm + ep_comm


# ── Device Detection ───────────────────────────────────────────────────

def detect_gpus() -> List[GPUDevice]:
    """Detect available GPUs on the system"""
    devices = []

    # Try nvidia-smi
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,driver_version,pcie.link.gen.max,pcie.link.width.max",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    idx, name, vram_total, vram_free, driver, pcie_gen, pcie_width = parts[:7]
                    vram_total = int(vram_total)
                    vram_free = int(vram_free)

                    # Estimate PCIe bandwidth
                    pcie_gen = int(pcie_gen)
                    pcie_width = int(pcie_width)
                    pcie_bw = pcie_gen * pcie_width * 1.0  # GB/s per lane per gen

                    # Check for NVLink
                    nvlink_bw = 0.0
                    try:
                        nvlink_result = subprocess.run(
                            ["nvidia-smi", "nvlink", "--query-gpu=index,nvlink.bandwidth",
                             "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, timeout=5
                        )
                        # Parse NVLink bandwidth if available
                    except Exception:
                        pass

                    # Compute capability
                    cc_map = {
                        "H100": "9.0", "A100": "8.0", "RTX 4090": "8.9", "RTX 3090": "8.6",
                        "V100": "7.0", "T4": "7.5", "A10G": "8.0",
                    }
                    cc = "8.0"
                    for k, v in cc_map.items():
                        if k.lower() in name.lower():
                            cc = v
                            break

                    devices.append(GPUDevice(
                        index=int(idx),
                        name=name,
                        vendor=GPUVendor.NVIDIA,
                        vram_total_mb=vram_total,
                        vram_free_mb=vram_free,
                        compute_capability=cc,
                        pcie_bandwidth_gb_s=pcie_bw,
                        nvlink_bandwidth_gb_s=nvlink_bw,
                        tensor_cores="tensor" in name.lower() or any(x in name for x in ["H100", "A100", "RTX", "V100", "T4"]),
                        driver_version=driver,
                    ))
    except Exception as e:
        print(f"NVIDIA GPU detection failed: {e}")

    # Try ROCm for AMD
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram"],
            capture_output=True, text=True, timeout=10
        )
        # Parse ROCm output
    except Exception:
        pass

    return devices


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Multi-GPU Resource Planner")
    parser.add_argument("--model-size", type=str, default="70B", help="Model size (e.g., 7B, 70B, 175B)")
    parser.add_argument("--num-experts", type=int, default=8, help="Number of experts")
    parser.add_argument("--experts-per-token", type=int, default=2, help="Experts per token")
    parser.add_argument("--context", type=int, default=4096, help="Context length")
    parser.add_argument("--dtype", type=str, default="fp16", help="Data type")
    parser.add_argument("--strategy", type=str, default="hybrid", help="Parallelism strategy")
    parser.add_argument("--max-gpus", type=int, help="Maximum GPUs to use")
    parser.add_argument("--list-gpus", action="store_true", help="List detected GPUs")

    args = parser.parse_args()

    devices = detect_gpus()

    if args.list_gpus:
        print("Detected GPUs:")
        for d in devices:
            print(f"  GPU {d.index}: {d.name} ({d.vram_free_mb}/{d.vram_total_mb} MB free, {d.compute_capability})")
        return

    if not devices:
        print("No GPUs detected!")
        return

    # Parse model size
    size_map = {
        "7B": {"dense": 14000, "expert": 2000, "layers": 32, "hidden": 4096, "heads": 32, "kv_heads": 8, "head_dim": 128},
        "70B": {"dense": 140000, "expert": 20000, "layers": 80, "hidden": 8192, "heads": 64, "kv_heads": 8, "head_dim": 128},
        "175B": {"dense": 350000, "expert": 50000, "layers": 96, "hidden": 12288, "heads": 96, "kv_heads": 16, "head_dim": 128},
    }
    model_config = size_map.get(args.model_size.upper(), size_map["70B"])

    model = ModelRequirements(
        dense_params_mb=model_config["dense"],
        expert_params_mb=model_config["expert"],
        num_experts=args.num_experts,
        experts_per_token=args.experts_per_token,
        num_layers=model_config["layers"],
        hidden_size=model_config["hidden"],
        num_attention_heads=model_config["heads"],
        kv_heads=model_config["kv_heads"],
        head_dim=model_config["head_dim"],
        context_length=args.context,
        dtype=args.dtype,
    )

    planner = MultiGPUPlanner(devices)
    strategy = ParallelismStrategy(args.strategy)

    plans = planner.plan_placement(model, strategy, args.max_gpus)

    print(f"\n📋 Placement Plans for {args.model_size} MoE ({args.num_experts} experts, top-{args.experts_per_token})")
    print(f"Context: {args.context}, Dtype: {args.dtype}")
    print(f"Available GPUs: {len(devices)}")
    print("=" * 80)

    for i, plan in enumerate(plans[:10]):
        print(f"\nPlan {i + 1}: {plan.strategy.value}")
        print(f"  GPUs: {plan.gpu_indices} (TP={plan.tensor_parallel_size}, PP={plan.pipeline_parallel_size}, EP={plan.expert_parallel_size}, DP={plan.data_parallel_size})")
        print(f"  VRAM/GPU: {plan.estimated_vram_per_gpu_mb} MB")
        print(f"  Latency: {plan.estimated_latency_ms:.1f} ms")
        print(f"  Throughput: {plan.estimated_throughput_tok_s:.1f} tok/s")
        print(f"  Comm overhead: {plan.communication_overhead_ms:.1f} ms")
        if plan.layers_per_gpu:
            print(f"  Layers/GPU: {plan.layers_per_gpu}")
        if plan.experts_per_gpu:
            print(f"  Experts/GPU: {plan.experts_per_gpu}")

    if not plans:
        print("No valid placement plans found. Try reducing model size or adding GPUs.")


if __name__ == "__main__":
    main()