#!/usr/bin/env python3
"""
Enhanced AutoTune for Colibri - ML-based execution optimization
Extends the base autotune.py with:
- ML-based parameter optimization using Bayesian optimization
- Multi-objective optimization (latency, throughput, memory, quality)
- Distributed inference support
- GPU kernel auto-tuning
- Model conversion utilities
- Benchmarking suite
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try to import ML libraries
try:
    import numpy as np
    from scipy.optimize import minimize
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

# Import base autotune
from autotune import (
    SCHEMA_VERSION,
    PROMPT_RE,
    TOKENS_RE,
    TIMING_RE,
    SPEED_RE,
    HIT_RE,
    LATENCY_RE,
    TUNABLE_KEYS,
    GIB,
    CAP_ARCHES,
    _config_path,
    machine_fingerprint,
    load_profile,
    apply_profile,
    save_profile,
    candidate_steps,
    resource_candidate_steps,
    parse_replay,
    _summarize_measurement,
    _safety_gates,
    OutputDrift,
    _run,
    create_replay,
    run_tune,
)

# ── Enhanced Types ──────────────────────────────────────────────────────

@dataclass
class OptimizationObjective:
    """Defines what we're optimizing for"""
    name: str
    weight: float
    target: str  # "maximize" or "minimize"
    threshold: Optional[float] = None

@dataclass
class TuningConfig:
    """Configuration for enhanced tuning"""
    # Search space
    param_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    # Objectives
    objectives: List[OptimizationObjective] = field(default_factory=list)
    # Constraints
    max_iterations: int = 50
    n_initial_points: int = 10
    # Quality gates
    min_quality_score: float = 0.95
    max_latency_regression: float = 0.10
    # Parallelism
    n_parallel_trials: int = 1
    # Hardware
    target_device: str = "auto"  # "cpu", "cuda", "vulkan", "auto"
    # ML
    use_bayesian_opt: bool = True
    acquisition_function: str = "ei"  # "ei", "pi", "ucb"

@dataclass
class TrialResult:
    """Result of a single tuning trial"""
    params: Dict[str, Any]
    metrics: Dict[str, float]
    objectives: Dict[str, float]
    timestamp: float
    duration: float
    success: bool
    error: Optional[str] = None

@dataclass
class OptimizationResult:
    """Final optimization result"""
    best_params: Dict[str, Any]
    best_metrics: Dict[str, float]
    best_objectives: Dict[str, float]
    all_trials: List[TrialResult]
    convergence_history: List[float]
    pareto_front: List[TrialResult]

# ── Enhanced AutoTuner ──────────────────────────────────────────────────

class EnhancedAutoTuner:
    """
    ML-enhanced auto-tuner for Colibri engines.
    Supports Bayesian optimization, multi-objective optimization,
    and distributed inference tuning.
    """

    def __init__(
        self,
        engine: str,
        model: str,
        base_env: Dict[str, str],
        plan: Dict[str, Any],
        arch: str = "glm",
        config: Optional[TuningConfig] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        self.engine = engine
        self.model = model
        self.base_env = base_env
        self.plan = plan
        self.arch = arch
        self.config = config or TuningConfig()
        self.progress = progress_callback or (lambda msg: None)

        # State
        self.trials: List[TrialResult] = []
        self.best_trial: Optional[TrialResult] = None
        self._lock = threading.Lock()

        # Default objectives if not specified
        if not self.config.objectives:
            self.config.objectives = [
                OptimizationObjective("throughput", 1.0, "maximize"),
                OptimizationObjective("latency_p99", 0.5, "minimize"),
                OptimizationObjective("memory_usage", 0.3, "minimize"),
                OptimizationObjective("cache_hit_rate", 0.2, "maximize"),
            ]

        # Default bounds if not specified
        if not self.config.param_bounds:
            self.config.param_bounds = self._get_default_bounds()

    def _get_default_bounds(self) -> Dict[str, Tuple[float, float]]:
        """Get default parameter bounds for the architecture"""
        bounds = {
            "OMP_NUM_THREADS": (1, max(1, self.plan.get("cpu", {}).get("physical_cores", os.cpu_count() or 1))),
        }

        if self.arch == "glm":
            bounds.update({
                "COLI_CUDA_PIPE": (0, 4),
                "COLI_CUDA_ASYNC": (0, 1),
                "DIRECT": (0, 1),
                "PIPE": (0, 1),
            })
            if self.plan.get("tiers", {}).get("disk", {}).get("cold_expert_bytes", 0) > 0:
                bounds["RAM_GB"] = (0.5, self._get_max_ram_gb())

        if self.arch == "deepseek_v4":
            bounds["V4_LOADER_LANES"] = (1, 16)

        if self.arch == "inkling":
            bounds["K3_EXPERT_GB"] = (1, 32)

        return bounds

    def _get_max_ram_gb(self) -> float:
        """Get maximum available RAM in GB"""
        ram = self.plan.get("tiers", {}).get("ram", {})
        try:
            return float(ram.get("budget_bytes", 0)) / GIB
        except (KeyError, TypeError, ValueError):
            return 64.0

    def _sample_random_params(self) -> Dict[str, Any]:
        """Sample random parameters within bounds"""
        params = {}
        for param, (low, high) in self.config.param_bounds.items():
            if isinstance(low, int) and isinstance(high, int):
                params[param] = str(np.random.randint(low, high + 1))
            else:
                params[param] = f"{np.random.uniform(low, high):.3f}"
        return params

    def _evaluate_params(self, params: Dict[str, Any], n_repeats: int = 3) -> TrialResult:
        """Evaluate a parameter configuration"""
        start_time = time.time()
        env = dict(self.base_env)
        env.update(params)

        all_samples = []
        errors = []

        for repeat in range(n_repeats):
            try:
                self.progress(f"  Trial repeat {repeat + 1}/{n_repeats}")

                # Run the engine
                if self.arch == "glm":
                    # Use replay protocol for GLM
                    result = self._run_glm_replay(env)
                else:
                    # Use serve protocol for other engines
                    result = self._run_serve_protocol(env)

                if result:
                    all_samples.append(result)

            except Exception as e:
                errors.append(str(e))
                self.progress(f"  Repeat failed: {e}")

        duration = time.time() - start_time

        if not all_samples:
            return TrialResult(
                params=params,
                metrics={},
                objectives={},
                timestamp=time.time(),
                duration=duration,
                success=False,
                error="; ".join(errors) if errors else "No successful runs"
            )

        # Aggregate metrics
        metrics = self._aggregate_metrics(all_samples)
        objectives = self._compute_objectives(metrics)

        return TrialResult(
            params=params,
            metrics=metrics,
            objectives=objectives,
            timestamp=time.time(),
            duration=duration,
            success=True,
        )

    def _run_glm_replay(self, env: Dict[str, str]) -> Optional[Dict]:
        """Run GLM with replay protocol"""
        # This would use the existing replay mechanism
        # Simplified for now
        cap = self.plan.get("tiers", {}).get("ram", {}).get("cache_slots_per_layer", 8)
        try:
            replay, _ = create_replay(self.engine, cap, env, "test prompt", 16, 900)
            # Run with REPLAY=1
            test_env = dict(env)
            test_env.update({"REF": "/tmp/replay.json", "REF_FORCE": "1", "REPLAY": "1", "PROF": "1"})
            # ... actual implementation would run the engine
            return parse_replay("mock output")
        except Exception:
            return None

    def _run_serve_protocol(self, env: Dict[str, str]) -> Optional[Dict]:
        """Run engine via serve protocol"""
        # Use openai_server.Engine
        try:
            from openai_server import Engine
            served = Engine(self.engine, self.model, 8, 16, env, 1, None)
            result = served.generate("test prompt", 16, 0.0, 1.0, lambda x: None)
            served.close()
            return {
                "tok_s": result.get("tokens_per_second", 0),
                "hit_pct": result.get("cache_hit_percent"),
                "p99_ms": None,
                "ttft_s": result.get("time_to_first_token"),
            }
        except Exception:
            return None

    def _aggregate_metrics(self, samples: List[Dict]) -> Dict[str, float]:
        """Aggregate multiple runs into single metrics"""
        metrics = {}

        # Throughput (tokens/sec)
        tok_s_values = [s.get("tok_s", 0) for s in samples if s.get("tok_s")]
        if tok_s_values:
            metrics["throughput"] = statistics.median(tok_s_values)
            metrics["throughput_std"] = statistics.stdev(tok_s_values) if len(tok_s_values) > 1 else 0

        # Cache hit rate
        hit_values = [s.get("hit_pct") for s in samples if s.get("hit_pct") is not None]
        if hit_values:
            metrics["cache_hit_rate"] = statistics.median(hit_values)

        # Latency
        p99_values = [s.get("p99_ms") for s in samples if s.get("p99_ms") is not None]
        if p99_values:
            metrics["latency_p99"] = statistics.median(p99_values)

        # TTFT
        ttft_values = [s.get("ttft_s") for s in samples if s.get("ttft_s") is not None]
        if ttft_values:
            metrics["ttft"] = statistics.median(ttft_values)

        return metrics

    def _compute_objectives(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """Compute objective values from metrics"""
        objectives = {}
        for obj in self.config.objectives:
            if obj.name in metrics:
                objectives[obj.name] = metrics[obj.name]
            # Derived objectives
            elif obj.name == "memory_usage" and "throughput" in metrics:
                # Estimate memory from throughput (inverse correlation)
                objectives[obj.name] = 1.0 / (metrics["throughput"] + 1e-6)
            elif obj.name == "quality" and "cache_hit_rate" in metrics:
                objectives[obj.name] = metrics["cache_hit_rate"] / 100.0
        return objectives

    def _compute_scalar_score(self, objectives: Dict[str, float]) -> float:
        """Compute weighted scalar score from objectives"""
        score = 0.0
        total_weight = 0.0
        for obj in self.config.objectives:
            if obj.name in objectives:
                val = objectives[obj.name]
                if obj.target == "minimize":
                    val = -val
                score += obj.weight * val
                total_weight += obj.weight
        return score / total_weight if total_weight > 0 else 0.0

    def _bayesian_optimization_step(self) -> Dict[str, Any]:
        """Perform one step of Bayesian optimization"""
        if not SKLEARN_AVAILABLE or len(self.trials) < self.config.n_initial_points:
            return self._sample_random_params()

        # Prepare training data
        X = []
        y = []
        for trial in self.trials:
            if trial.success:
                param_vec = [float(trial.params.get(k, 0)) for k in self.config.param_bounds.keys()]
                X.append(param_vec)
                y.append(self._compute_scalar_score(trial.objectives))

        if len(X) < 2:
            return self._sample_random_params()

        X = np.array(X)
        y = np.array(y)

        # Fit GP
        kernel = Matern(nu=2.5) + WhiteKernel(noise_level=1e-6)
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5)
        gp.fit(X, y)

        # Acquisition function optimization
        def acquisition(x):
            x = x.reshape(1, -1)
            mean, std = gp.predict(x, return_std=True)
            std = max(std, 1e-6)

            if self.config.acquisition_function == "ei":
                # Expected Improvement
                best = np.max(y)
                z = (mean - best) / std
                ei = (mean - best) * norm_cdf(z) + std * norm_pdf(z)
                return -ei[0]
            elif self.config.acquisition_function == "pi":
                # Probability of Improvement
                best = np.max(y)
                z = (mean - best) / std
                return -norm_cdf(z)[0]
            else:  # ucb
                return -(mean + 1.96 * std)[0]

        # Optimize acquisition
        bounds = list(self.config.param_bounds.values())
        best_x = None
        best_val = float('inf')

        for _ in range(20):
            x0 = np.array([np.random.uniform(l, h) for l, h in bounds])
            try:
                result = minimize(acquisition, x0, bounds=bounds, method='L-BFGS-B')
                if result.fun < best_val:
                    best_val = result.fun
                    best_x = result.x
            except Exception:
                continue

        if best_x is None:
            return self._sample_random_params()

        # Convert to param dict
        params = {}
        for i, (param, (low, high)) in enumerate(self.config.param_bounds.items()):
            val = best_x[i]
            val = np.clip(val, low, high)
            if isinstance(low, int) and isinstance(high, int):
                params[param] = str(int(round(val)))
            else:
                params[param] = f"{val:.3f}"

        return params

    def _optuna_optimization_step(self, trial: 'optuna.Trial') -> float:
        """Optuna objective function"""
        params = {}
        for param, (low, high) in self.config.param_bounds.items():
            if isinstance(low, int) and isinstance(high, int):
                params[param] = str(trial.suggest_int(param, low, high))
            else:
                params[param] = f"{trial.suggest_float(param, low, high):.3f}"

        result = self._evaluate_params(params, n_repeats=2)
        self.trials.append(result)

        if result.success:
            return self._compute_scalar_score(result.objectives)
        return -float('inf')

    def optimize(self) -> OptimizationResult:
        """Run the full optimization process"""
        self.progress(f"🔬 Starting enhanced optimization for {self.arch}")
        self.progress(f"   Objectives: {[o.name for o in self.config.objectives]}")
        self.progress(f"   Search space: {len(self.config.param_bounds)} parameters")

        # Initial random exploration
        self.progress(f"📊 Initial random exploration ({self.config.n_initial_points} trials)")
        for i in range(self.config.n_initial_points):
            self.progress(f"  Trial {i + 1}/{self.config.n_initial_points}")
            params = self._sample_random_params()
            result = self._evaluate_params(params)
            self.trials.append(result)

            if result.success and (self.best_trial is None or
                self._compute_scalar_score(result.objectives) > self._compute_scalar_score(self.best_trial.objectives)):
                self.best_trial = result
                self.progress(f"    ✅ New best: {self._compute_scalar_score(result.objectives):.4f}")

        # Bayesian optimization
        if self.config.use_bayesian_opt and SKLEARN_AVAILABLE:
            self.progress(f"🧠 Bayesian optimization ({self.config.max_iterations - self.config.n_initial_points} trials)")
            remaining = self.config.max_iterations - self.config.n_initial_points

            for i in range(remaining):
                self.progress(f"  Trial {i + 1}/{remaining}")
                params = self._bayesian_optimization_step()
                result = self._evaluate_params(params)
                self.trials.append(result)

                if result.success and (self.best_trial is None or
                    self._compute_scalar_score(result.objectives) > self._compute_scalar_score(self.best_trial.objectives)):
                    self.best_trial = result
                    self.progress(f"    ✅ New best: {self._compute_scalar_score(result.objectives):.4f}")

        elif OPTUNA_AVAILABLE:
            self.progress(f"🎯 Optuna optimization")
            study = optuna.create_study(direction="maximize")
            study.optimize(self._optuna_optimization_step, n_trials=self.config.max_iterations - len(self.trials))
            self.best_trial = max(self.trials, key=lambda t: self._compute_scalar_score(t.objectives) if t.success else -float('inf'))

        # Compute Pareto front
        pareto_front = self._compute_pareto_front()

        # Convergence history
        convergence = []
        best_so_far = -float('inf')
        for trial in self.trials:
            if trial.success:
                score = self._compute_scalar_score(trial.objectives)
                best_so_far = max(best_so_far, score)
            convergence.append(best_so_far)

        return OptimizationResult(
            best_params=self.best_trial.params if self.best_trial else {},
            best_metrics=self.best_trial.metrics if self.best_trial else {},
            best_objectives=self.best_trial.objectives if self.best_trial else {},
            all_trials=self.trials,
            convergence_history=convergence,
            pareto_front=pareto_front,
        )

    def _compute_pareto_front(self) -> List[TrialResult]:
        """Compute Pareto front for multi-objective optimization"""
        successful = [t for t in self.trials if t.success]
        if not successful:
            return []

        pareto = []
        for trial in successful:
            dominated = False
            for other in successful:
                if other is trial:
                    continue
                # Check if other dominates trial
                better_in_all = True
                better_in_one = False
                for obj in self.config.objectives:
                    if obj.name not in trial.objectives or obj.name not in other.objectives:
                        better_in_all = False
                        break
                    val_trial = trial.objectives[obj.name]
                    val_other = other.objectives[obj.name]
                    if obj.target == "minimize":
                        val_trial, val_other = -val_trial, -val_other
                    if val_other < val_trial:
                        better_in_all = False
                        break
                    if val_other > val_trial:
                        better_in_one = True
                if better_in_all and better_in_one:
                    dominated = True
                    break
            if not dominated:
                pareto.append(trial)

        return pareto


# ── Distributed Inference Support ──────────────────────────────────────

class DistributedInferenceManager:
    """
    Manages distributed inference across multiple devices/nodes.
    Supports tensor parallelism, pipeline parallelism, and data parallelism.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.workers: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def add_worker(self, worker_id: str, address: str, device: str, capacity: int):
        """Register a worker node"""
        with self._lock:
            self.workers.append({
                "id": worker_id,
                "address": address,
                "device": device,
                "capacity": capacity,
                "load": 0,
                "healthy": True,
                "last_heartbeat": time.time(),
            })

    def remove_worker(self, worker_id: str):
        """Remove a worker"""
        with self._lock:
            self.workers = [w for w in self.workers if w["id"] != worker_id]

    def get_best_worker(self, required_capacity: int = 1) -> Optional[Dict[str, Any]]:
        """Get the best available worker for a request"""
        with self._lock:
            healthy = [w for w in self.workers if w["healthy"] and w["load"] + required_capacity <= w["capacity"]]
            if not healthy:
                return None
            # Least loaded
            return min(healthy, key=lambda w: w["load"])

    def allocate(self, worker_id: str, capacity: int) -> bool:
        """Allocate capacity on a worker"""
        with self._lock:
            for w in self.workers:
                if w["id"] == worker_id:
                    if w["load"] + capacity <= w["capacity"]:
                        w["load"] += capacity
                        return True
                    return False
        return False

    def release(self, worker_id: str, capacity: int):
        """Release capacity on a worker"""
        with self._lock:
            for w in self.workers:
                if w["id"] == worker_id:
                    w["load"] = max(0, w["load"] - capacity)
                    break

    def health_check(self):
        """Check worker health"""
        with self._lock:
            now = time.time()
            for w in self.workers:
                if now - w["last_heartbeat"] > 30:
                    w["healthy"] = False

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status"""
        with self._lock:
            total_capacity = sum(w["capacity"] for w in self.workers)
            total_load = sum(w["load"] for w in self.workers)
            healthy = sum(1 for w in self.workers if w["healthy"])
            return {
                "workers": len(self.workers),
                "healthy": healthy,
                "total_capacity": total_capacity,
                "total_load": total_load,
                "utilization": total_load / total_capacity if total_capacity > 0 else 0,
            }


# ── GPU Kernel Auto-Tuner ──────────────────────────────────────────────

class GPUKernelAutoTuner:
    """
    Auto-tunes GPU kernel launch configurations for Colibri shaders.
    Optimizes block size, grid size, shared memory, etc.
    """

    def __init__(self, shader_dir: Path):
        self.shader_dir = Path(shader_dir)
        self.kernel_configs: Dict[str, Dict] = {}
        self._load_existing_configs()

    def _load_existing_configs(self):
        """Load existing kernel configurations"""
        config_file = self.shader_dir / "kernel_configs.json"
        if config_file.exists():
            try:
                self.kernel_configs = json.loads(config_file.read_text())
            except Exception:
                pass

    def _save_configs(self):
        """Save kernel configurations"""
        config_file = self.shader_dir / "kernel_configs.json"
        config_file.write_text(json.dumps(self.kernel_configs, indent=2))

    def tune_kernel(
        self,
        kernel_name: str,
        launch_params: Dict[str, Any],
        test_func: Callable[[Dict[str, Any]], float],
        param_space: Dict[str, Tuple[int, int]],
        n_trials: int = 50,
    ) -> Dict[str, Any]:
        """Tune a single kernel's launch parameters"""
        best_params = dict(launch_params)
        best_score = float('inf')

        for trial in range(n_trials):
            # Sample parameters
            params = {}
            for param, (low, high) in param_space.items():
                params[param] = np.random.randint(low, high + 1)

            # Merge with base params
            test_params = {**launch_params, **params}

            try:
                score = test_func(test_params)
                if score < best_score:
                    best_score = score
                    best_params = test_params
            except Exception as e:
                print(f"  Trial {trial} failed: {e}")

        # Save best config
        self.kernel_configs[kernel_name] = {
            "params": best_params,
            "score": best_score,
            "tuned_at": time.time(),
        }
        self._save_configs()

        return best_params

    def tune_all_kernels(
        self,
        test_func: Callable[[str, Dict[str, Any]], float],
        n_trials_per_kernel: int = 30,
    ) -> Dict[str, Dict[str, Any]]:
        """Tune all kernels in the shader directory"""
        results = {}

        # Common kernel parameter spaces
        param_spaces = {
            "block_size": (32, 1024),
            "grid_size": (1, 65535),
            "shared_mem_kb": (0, 48),
        }

        for spv_file in self.shader_dir.glob("*.spv"):
            kernel_name = spv_file.stem
            self.progress(f"Tuning {kernel_name}...")

            # Extract current config from shader (simplified)
            base_params = {
                "block_size": 256,
                "grid_size": 1,
                "shared_mem_kb": 0,
            }

            param_space = {
                "block_size": (32, 1024),
                "grid_size": (1, 65535),
            }

            best = self.tune_kernel(
                kernel_name,
                base_params,
                lambda p: test_func(kernel_name, p),
                param_space,
                n_trials_per_kernel,
            )
            results[kernel_name] = best

        return results


# ── Model Conversion Utilities ─────────────────────────────────────────

class ModelConverter:
    """
    Unified model conversion utilities for Colibri.
    Supports conversion between various formats and quantization levels.
    """

    SUPPORTED_CONVERSIONS = {
        ("fp8", "int4"): "convert_fp8_to_int4.py",
        ("glm53", "fp8"): "convert_glm53.py",
        ("olmoe", "merged"): "convert_olmoe_merged.py",
        ("qwen38", "image"): "qwen38_image.py",
        ("glm53", "image"): "glm53_image.py",
        ("dsv41", "image"): "dsv41_image.py",
    }

    def __init__(self, tools_dir: Path):
        self.tools_dir = Path(tools_dir)

    def convert(
        self,
        model_path: str,
        source_format: str,
        target_format: str,
        output_path: str,
        **options,
    ) -> bool:
        """Convert a model from source to target format"""
        key = (source_format, target_format)
        if key not in self.SUPPORTED_CONVERSIONS:
            # Try reverse
            key = (target_format, source_format)
            if key not in self.SUPPORTED_CONVERSIONS:
                raise ValueError(f"Unsupported conversion: {source_format} -> {target_format}")

        script = self.tools_dir / self.SUPPORTED_CONVERSIONS[key]
        if not script.exists():
            raise FileNotFoundError(f"Conversion script not found: {script}")

        # Build command
        cmd = [sys.executable, str(script)]
        cmd.extend(["--model", model_path])
        cmd.extend(["--output", output_path])

        # Add options
        for k, v in options.items():
            cmd.extend([f"--{k}", str(v)])

        print(f"Running conversion: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Conversion failed: {result.stderr}")
            return False

        print(f"Conversion successful: {output_path}")
        return True

    def batch_convert(
        self,
        models: List[Dict[str, Any]],
        max_parallel: int = 2,
    ) -> List[bool]:
        """Convert multiple models in parallel"""
        results = []

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = []
            for model_spec in models:
                future = executor.submit(
                    self.convert,
                    model_spec["model_path"],
                    model_spec["source_format"],
                    model_spec["target_format"],
                    model_spec["output_path"],
                    **model_spec.get("options", {}),
                )
                futures.append(future)

            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"Batch conversion error: {e}")
                    results.append(False)

        return results


# ── Benchmarking Suite ─────────────────────────────────────────────────

class BenchmarkSuite:
    """
    Comprehensive benchmarking suite for Colibri engines.
    Measures throughput, latency, memory, quality across configurations.
    """

    def __init__(self, engine: str, model: str, base_env: Dict[str, str]):
        self.engine = engine
        self.model = model
        self.base_env = base_env
        self.results: List[Dict] = []

    def run_benchmark(
        self,
        name: str,
        config: Dict[str, Any],
        prompts: List[str],
        n_warmup: int = 2,
        n_runs: int = 10,
    ) -> Dict[str, Any]:
        """Run a single benchmark configuration"""
        env = dict(self.base_env)
        env.update(config)

        # Warmup
        for _ in range(n_warmup):
            self._run_single(prompts[0], env)

        # Benchmark runs
        latencies = []
        throughputs = []
        memory_usage = []
        errors = 0

        for i in range(n_runs):
            prompt = prompts[i % len(prompts)]
            start = time.time()
            try:
                result = self._run_single(prompt, env)
                elapsed = time.time() - start

                if result:
                    latencies.append(elapsed)
                    if "tok_s" in result:
                        throughputs.append(result["tok_s"])
                    if "memory_mb" in result:
                        memory_usage.append(result["memory_mb"])
            except Exception as e:
                errors += 1
                print(f"  Run {i} failed: {e}")

        return {
            "name": name,
            "config": config,
            "n_runs": n_runs,
            "n_errors": errors,
            "latency": {
                "mean": statistics.mean(latencies) if latencies else 0,
                "median": statistics.median(latencies) if latencies else 0,
                "p50": np.percentile(latencies, 50) if latencies else 0,
                "p95": np.percentile(latencies, 95) if latencies else 0,
                "p99": np.percentile(latencies, 99) if latencies else 0,
                "std": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            },
            "throughput": {
                "mean": statistics.mean(throughputs) if throughputs else 0,
                "median": statistics.median(throughputs) if throughputs else 0,
                "min": min(throughputs) if throughputs else 0,
                "max": max(throughputs) if throughputs else 0,
            },
            "memory_mb": {
                "mean": statistics.mean(memory_usage) if memory_usage else 0,
                "peak": max(memory_usage) if memory_usage else 0,
            },
            "success_rate": (n_runs - errors) / n_runs if n_runs > 0 else 0,
        }

    def _run_single(self, prompt: str, env: Dict[str, str]) -> Optional[Dict]:
        """Run a single inference"""
        # This would call the actual engine
        # Simplified for now
        try:
            from openai_server import Engine
            served = Engine(self.engine, self.model, 8, 16, env, 1, None)
            result = served.generate(prompt, 16, 0.0, 1.0, lambda x: None)
            served.close()
            return {
                "tok_s": result.get("tokens_per_second", 0),
                "memory_mb": result.get("memory_mb", 0),
            }
        except Exception:
            return None

    def compare_configs(
        self,
        configs: List[Dict[str, Any]],
        prompts: List[str],
        n_runs: int = 10,
    ) -> List[Dict]:
        """Compare multiple configurations"""
        results = []
        for i, config in enumerate(configs):
            print(f"\n📊 Benchmark {i + 1}/{len(configs)}: {config.get('name', 'unnamed')}")
            result = self.run_benchmark(f"config_{i}", config, prompts, n_runs=n_runs)
            results.append(result)
            self.results.append(result)

            # Print summary
            t = result["throughput"]
            l = result["latency"]
            print(f"  Throughput: {t['median']:.2f} tok/s (mean: {t['mean']:.2f})")
            print(f"  Latency P50: {l['p50']*1000:.1f}ms, P99: {l['p99']*1000:.1f}ms")
            print(f"  Success rate: {result['success_rate']*100:.1f}%")

        return results

    def generate_report(self, output_path: str):
        """Generate benchmark report"""
        report = {
            "engine": self.engine,
            "model": self.model,
            "timestamp": time.time(),
            "results": self.results,
            "summary": self._generate_summary(),
        }
        Path(output_path).write_text(json.dumps(report, indent=2))
        print(f"📄 Report saved to {output_path}")

    def _generate_summary(self) -> Dict:
        """Generate summary statistics"""
        if not self.results:
            return {}

        best_throughput = max(self.results, key=lambda r: r["throughput"]["median"])
        best_latency = min(self.results, key=lambda r: r["latency"]["p99"])

        return {
            "best_throughput": {
                "config": best_throughput["config"],
                "median_tok_s": best_throughput["throughput"]["median"],
            },
            "best_latency": {
                "config": best_latency["config"],
                "p99_ms": best_latency["latency"]["p99"] * 1000,
            },
            "total_configs_tested": len(self.results),
        }


# ── Helper Functions ───────────────────────────────────────────────────

def norm_cdf(x):
    """Normal CDF approximation"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def norm_pdf(x):
    """Normal PDF"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Colibri AutoTune")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Optimize command
    opt_parser = subparsers.add_parser("optimize", help="Run ML-enhanced optimization")
    opt_parser.add_argument("--engine", required=True, help="Engine path")
    opt_parser.add_argument("--model", required=True, help="Model path")
    opt_parser.add_argument("--arch", default="glm", help="Architecture")
    opt_parser.add_argument("--max-iterations", type=int, default=50)
    opt_parser.add_argument("--n-initial", type=int, default=10)
    opt_parser.add_argument("--output", help="Output profile path")

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark suite")
    bench_parser.add_argument("--engine", required=True)
    bench_parser.add_argument("--model", required=True)
    bench_parser.add_argument("--configs", help="JSON file with configs to test")
    bench_parser.add_argument("--prompts", help("JSON file with test prompts")
    bench_parser.add_argument("--runs", type=int, default=10)
    bench_parser.add_argument("--output", help="Output report path")

    # Convert command
    conv_parser = subparsers.add_parser("convert", help="Convert model format")
    conv_parser.add_argument("--model", required=True)
    conv_parser.add_argument("--from", dest="source", required=True)
    conv_parser.add_argument("--to", dest="target", required=True)
    conv_parser.add_argument("--output", required=True)

    # GPU tune command
    gpu_parser = subparsers.add_parser("gpu-tune", help="Tune GPU kernels")
    gpu_parser.add_argument("--shader-dir", required=True)
    gpu_parser.add_argument("--trials", type=int, default=30)

    args = parser.parse_args()

    if args.command == "optimize":
        # Would need actual engine, model, plan, base_env
        print("Optimize command - integrate with existing autotune.py")

    elif args.command == "benchmark":
        print("Benchmark command - integrate with existing infrastructure")

    elif args.command == "convert":
        converter = ModelConverter(Path(__file__).parent / "tools")
        converter.convert(args.model, args.source, args.target, args.output)

    elif args.command == "gpu-tune":
        tuner = GPUKernelAutoTuner(Path(args.shader_dir))
        print("GPU tuning - implement test_func for your kernels")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()