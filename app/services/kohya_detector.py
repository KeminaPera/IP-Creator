"""
Kohya Environment Detection Service

Detects and validates Kohya-ss installation, checks dependencies,
and verifies GPU availability for training.
"""
from pathlib import Path
import subprocess
import sys
from typing import Dict, Any, Optional
from app.utils.logger import logger


class KohyaDetector:
    """
    Service for detecting and validating Kohya-ss environment.
    """
    
    def __init__(self):
        self.common_paths = [
            Path("kohya_ss"),
            Path("../kohya_ss"),
            Path("../../kohya_ss"),
            Path.home() / "kohya_ss",
            Path.home() / "kohya-sd",
        ]
    
    def detect_kohya(self) -> Dict[str, Any]:
        """
        Detect Kohya-ss installation.
        
        Returns detection result with installation status and paths.
        """
        logger.info("Detecting Kohya-ss installation...")
        
        result = {
            "installed": False,
            "kohya_path": None,
            "train_script": None,
            "python_executable": None,
            "version": None,
            "errors": [],
            "warnings": [],
        }
        
        # 1. Search for Kohya installation
        kohya_path = self._find_kohya_installation()
        
        if not kohya_path:
            result["errors"].append(
                "Kohya-ss not found. Please install Kohya-ss first. "
                "See: https://github.com/bmaltais/kohya_ss"
            )
            logger.warning("Kohya-ss not found")
            return result
        
        result["installed"] = True
        result["kohya_path"] = str(kohya_path)
        logger.info(f"Found Kohya-ss at: {kohya_path}")
        
        # 2. Check training script
        train_script = kohya_path / "train_network.py"
        if not train_script.exists():
            # Try alternative locations
            alternatives = [
                kohya_path / "kohya_ss" / "train_network.py",
                kohya_path / "library" / "train_network.py",
            ]
            
            for alt in alternatives:
                if alt.exists():
                    train_script = alt
                    break
        
        if train_script.exists():
            result["train_script"] = str(train_script)
            logger.info(f"Found training script: {train_script}")
        else:
            result["warnings"].append(
                "Training script not found. Some features may not work."
            )
        
        # 3. Check Python environment
        python_exe = self._find_python_executable(kohya_path)
        if python_exe:
            result["python_executable"] = str(python_exe)
            
            # Check Python version
            try:
                version_output = subprocess.check_output(
                    [str(python_exe), "--version"],
                    stderr=subprocess.STDOUT,
                    text=True
                )
                result["python_version"] = version_output.strip()
                logger.info(f"Python version: {version_output.strip()}")
            except Exception as e:
                result["warnings"].append(f"Failed to check Python version: {e}")
        
        # 4. Check GPU availability
        gpu_info = self._check_gpu(python_exe)
        result.update(gpu_info)
        
        # 5. Check required packages
        packages = self._check_packages(python_exe)
        result["packages"] = packages
        
        return result
    
    def _find_kohya_installation(self) -> Optional[Path]:
        """Search for Kohya-ss installation in common locations."""
        
        # Check common paths
        for path in self.common_paths:
            if path.exists() and (path / "requirements.txt").exists():
                return path.resolve()
        
        # Check environment variable
        import os
        env_path = os.environ.get("KOHYA_PATH")
        if env_path:
            kohya_path = Path(env_path)
            if kohya_path.exists():
                return kohya_path.resolve()
        
        return None
    
    def _find_python_executable(self, kohya_path: Path) -> Optional[Path]:
        """Find Python executable in Kohya environment."""
        
        # Check for venv
        venv_python = kohya_path / "venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return venv_python
        
        # Check for conda environment
        conda_python = kohya_path / "python.exe"
        if conda_python.exists():
            return conda_python
        
        # Fallback to system Python
        return Path(sys.executable)
    
    def _check_gpu(self, python_exe: Optional[Path]) -> Dict[str, Any]:
        """Check GPU availability and CUDA version."""
        
        gpu_info = {
            "gpu_available": False,
            "gpu_name": None,
            "cuda_version": None,
            "vram_gb": None,
        }
        
        if not python_exe:
            return gpu_info
        
        try:
            # Check torch CUDA availability
            check_script = """
import torch
if torch.cuda.is_available():
    print(f"CUDA:{torch.version.cuda}")
    print(f"GPU:{torch.cuda.get_device_name(0)}")
    print(f"VRAM:{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}")
else:
    print("NO_CUDA")
"""
            result = subprocess.run(
                [str(python_exe), "-c", check_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.strip().split("\n")
                
                if output[0] != "NO_CUDA":
                    gpu_info["gpu_available"] = True
                    
                    for line in output:
                        if line.startswith("CUDA:"):
                            gpu_info["cuda_version"] = line.split(":", 1)[1]
                        elif line.startswith("GPU:"):
                            gpu_info["gpu_name"] = line.split(":", 1)[1]
                        elif line.startswith("VRAM:"):
                            gpu_info["vram_gb"] = float(line.split(":", 1)[1])
                    
                    logger.info(f"GPU detected: {gpu_info['gpu_name']} ({gpu_info['vram_gb']}GB)")
                else:
                    logger.warning("No GPU available, training will use CPU (slow)")
        
        except Exception as e:
            logger.warning(f"Failed to check GPU: {e}")
        
        return gpu_info
    
    def _check_packages(self, python_exe: Optional[Path]) -> Dict[str, Any]:
        """Check required Python packages."""
        
        packages = {
            "torch": {"installed": False, "version": None},
            "diffusers": {"installed": False, "version": None},
            "transformers": {"installed": False, "version": None},
            "accelerate": {"installed": False, "version": None},
        }
        
        if not python_exe:
            return packages
        
        try:
            # Get installed packages
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                installed = json.loads(result.stdout)
                
                for pkg_info in installed:
                    pkg_name = pkg_info["name"].lower()
                    
                    if pkg_name in packages:
                        packages[pkg_name]["installed"] = True
                        packages[pkg_name]["version"] = pkg_info["version"]
        
        except Exception as e:
            logger.warning(f"Failed to check packages: {e}")
        
        return packages
    
    def validate_environment(self) -> Dict[str, Any]:
        """
        Complete environment validation.
        
        Returns comprehensive validation result with recommendations.
        """
        detection = self.detect_kohya()
        
        validation = {
            "ready_for_training": False,
            "detection": detection,
            "recommendations": [],
            "errors": [],
        }
        
        # Check critical requirements
        if not detection["installed"]:
            validation["errors"].append("Kohya-ss is not installed")
            validation["recommendations"].append(
                "Install Kohya-ss: https://github.com/bmaltais/kohya_ss"
            )
            return validation
        
        if not detection.get("gpu_available"):
            validation["recommendations"].append(
                "GPU not detected. Training will be very slow on CPU. "
                "Consider using a GPU with at least 8GB VRAM."
            )
        
        if detection.get("vram_gb") and detection["vram_gb"] < 8:
            validation["recommendations"].append(
                f"VRAM is low ({detection['vram_gb']}GB). "
                "Consider using lower resolution or batch size."
            )
        
        # Check critical packages
        missing_packages = []
        for pkg_name, pkg_info in detection.get("packages", {}).items():
            if not pkg_info["installed"]:
                missing_packages.append(pkg_name)
        
        if missing_packages:
            validation["recommendations"].append(
                f"Missing packages: {', '.join(missing_packages)}"
            )
        
        # Determine if ready for training
        validation["ready_for_training"] = (
            detection["installed"] and 
            len(validation["errors"]) == 0
        )
        
        return validation
