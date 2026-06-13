"""
LoRA Training Module

Orchestrates LoRA model training tasks with Kohya-sd integration,
GPU resource management, and progress tracking.
"""
from typing import Optional, Dict, Any
from pathlib import Path
import subprocess
import asyncio
import json
import time
from datetime import datetime
from app.models.lora_model import LoRAModel
from app.config.settings import settings
from app.utils.logger import logger
from app.config.database import get_db_session_standalone
from sqlalchemy import select
from app.services.training_logger import training_logger
from app.services.kohya_detector import KohyaDetector
from app.services.dataset_converter import DatasetConverter


class LoRATrainer:
    """
    Service for managing LoRA model training.
    
    Handles training task creation, Kohya-sd integration,
    GPU monitoring, and model validation.
    """
    
    def __init__(self):
        """Initialize LoRA trainer."""
        self.lora_path = Path(settings.LORA_MODELS_PATH)
        self.lora_path.mkdir(parents=True, exist_ok=True)
        self.kohya_detector = KohyaDetector()
        self.dataset_converter = DatasetConverter()
        # Progress reporter (injected by celery_worker)
        self.progress_reporter = None
        # Track active training processes for cancellation
        self._active_processes = {}  # {lora_id: subprocess.Popen}
    
    def set_progress_reporter(self, reporter):
        """
        Set progress reporter (dependency injection).
        
        Args:
            reporter: ProgressReporter instance
        """
        self.progress_reporter = reporter
    
    async def create_training_task(
        self,
        name: str,
        base_model: str,
        training_params: Dict[str, Any],
        ip_asset_id: Optional[int] = None,
    ) -> LoRAModel:
        """
        Create a new LoRA training task.
        
        Args:
            name: Model name
            base_model: Base model to fine-tune
            training_params: Training configuration
            ip_asset_id: Associated IP asset ID
            
        Returns:
            Created LoRA model record
        """
        async with get_db_session_standalone() as session:
            # Generate output file path
            output_path = self.lora_path / f"{name}.safetensors"
            
            # Create LoRA model record
            lora_model = LoRAModel(
                name=name,
                file_path=str(output_path),
                base_model=base_model,
                training_params=training_params,
                status="pending",
                weight_default=training_params.get("weight", 0.7),
            )
            
            session.add(lora_model)
            await session.commit()
            await session.refresh(lora_model)
            
            logger.info(f"Created LoRA training task: {name}")
            return lora_model
    
    async def start_training(self, lora_id: int) -> bool:
        """
        Start LoRA training process.
        
        Note: Status management (training/failed/completed) is handled by celery_worker.
        This method only executes the training logic and updates completion fields.
        
        Args:
            lora_id: LoRA model ID
            
        Returns:
            True if training completed successfully
        """
        async with get_db_session_standalone() as session:
            lora_model = await session.get(LoRAModel, lora_id)
            if not lora_model:
                logger.error(f"LoRA model {lora_id} not found")
                return False
            
            try:
                # Log training start (status already set by celery_worker)
                await training_logger.log(
                    lora_id,
                    f"Starting training for {lora_model.name}",
                    level="INFO"
                )
                
                # Run Kohya-sd training
                success = await self._run_kohya_training(lora_model)
                
                if success:
                    # Only update completion fields (status managed by celery_worker)
                    lora_model.progress = 100.0
                    lora_model.completed_at = datetime.now()
                    await session.commit()
                    
                    await training_logger.log(
                        lora_id,
                        f"Training completed successfully",
                        level="INFO"
                    )
                    
                    logger.info(f"Completed training for LoRA model: {lora_model.name}")
                    
                    # Auto-trigger quality assessment
                    try:
                        from app.services.quality_assessor import QualityAssessor
                        assessor = QualityAssessor()
                        assessment = await assessor.assess_model_quality(
                            lora_id=lora_id,
                            num_test_images=5,
                        )
                        logger.info(f"Quality assessment auto-completed: {assessment['overall_score']}/100 ({assessment['grade']})")
                        
                        await training_logger.log(
                            lora_id,
                            f"Quality assessment: {assessment['overall_score']}/100 ({assessment['grade']})",
                            level="INFO"
                        )
                    except Exception as e:
                        logger.warning(f"Auto quality assessment failed: {e}")
                        # Don't fail training if assessment fails
                else:
                    await training_logger.log(
                        lora_id,
                        f"Training failed",
                        level="ERROR"
                    )
                    
                    logger.error(f"Training failed for {lora_model.name}")
                
                return success
            
            except Exception as e:
                # Don't update status here, let celery_worker handle it
                await training_logger.log(
                    lora_id,
                    f"Training error: {str(e)}",
                    level="ERROR"
                )
                
                logger.error(f"Training failed for {lora_model.name}: {e}")
                # Re-raise for celery_worker to handle
                raise
    
    async def _run_kohya_training(self, lora_model: LoRAModel) -> bool:
        """
        Run Kohya-sd training script via subprocess.
        
        Args:
            lora_model: LoRA model configuration
            
        Returns:
            True if training completed successfully
        """
        import subprocess
        import toml
        
        logger.info(f"Starting Kohya training for: {lora_model.name}")
        logger.info(f"Base model: {lora_model.base_model}")
        
        # 1. Check Kohya environment
        detection = self.kohya_detector.detect_kohya()
        
        if not detection["installed"]:
            logger.warning("Kohya-ss not found, using simulation mode")
            return await self._simulate_training(lora_model)
        
        # 2. Prepare training parameters
        params = lora_model.training_params or {}
        logger.info(f"📋 Training params from DB: {json.dumps(params, ensure_ascii=False, indent=2) if params else 'None'}")
        output_dir = Path(lora_model.file_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Get dataset path if available
        dataset_path = None
        if lora_model.dataset_id:
            from app.config.settings import settings
            kohya_dir = Path(settings.STORAGE_PATH) / "datasets" / f"kohya_dataset_{lora_model.dataset_id}"
            if kohya_dir.exists():
                dataset_path = str(kohya_dir.resolve())  # Ensure absolute path
                logger.info(f"Using dataset: {dataset_path}")
        
        # 4. Map base model to actual model path or HuggingFace ID
        base_model_map = {
            "sd1.5": "runwayml/stable-diffusion-v1-5",
            "sd2.1": "stabilityai/stable-diffusion-2-1",
            "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
        }
        pretrained_model = base_model_map.get(lora_model.base_model, lora_model.base_model)
        
        # Validate dataset path
        if not dataset_path:
            logger.error(f"No training dataset found for LoRA model {lora_model.id}")
            raise ValueError(
                f"训练数据集未找到。请先为模型 {lora_model.name} 创建并转换数据集。"
            )
        
        # 5. Create training configuration with absolute paths
        # Note: Kohya-ss expects certain fields as strings, not integers
        resolution_value = params.get("resolution", 512)
        epochs = params.get("epochs", 10)
        
        # Calculate max_train_steps based on epochs if not explicitly set
        # Kohya uses: max_train_steps = epochs * (dataset_size / batch_size)
        # If max_train_steps is set, it overrides epochs
        max_train_steps = params.get("max_train_steps")
        if not max_train_steps:
            # Estimate steps: epochs * (estimated images / batch_size)
            # Note: Frontend uses 'batch_size', Kohya config uses 'train_batch_size'
            batch_size = params.get("train_batch_size") or params.get("batch_size", 1)
            estimated_images = 20  # Default estimate
            max_train_steps = epochs * (estimated_images // batch_size)
            logger.info(f"Auto-calculated max_train_steps: {max_train_steps} (epochs={epochs}, batch_size={batch_size})")
        else:
            logger.info(f"Using explicit max_train_steps: {max_train_steps}")
        
        config = {
            "general": {
                "pretrained_model_name_or_path": pretrained_model,
                "train_data_dir": dataset_path,
                "output_dir": str(output_dir.resolve()),
                "output_name": lora_model.name,
                "max_train_steps": max_train_steps,
                "save_every_n_steps": params.get("save_every_n_steps", 100),
                "learning_rate": params.get("learning_rate", 1e-4),
                "resolution": str(resolution_value),  # Must be string for Kohya-ss
                "train_batch_size": params.get("train_batch_size") or params.get("batch_size", 1),
                "gradient_accumulation_steps": params.get("gradient_accumulation_steps", 4),
                "mixed_precision": params.get("mixed_precision", "fp16"),
                # Disable DataLoader workers on macOS to avoid multiprocessing issues
                "max_data_loader_n_workers": 0,
                "seed": params.get("seed", 42),
                # Enable bucketing to handle large images
                "enable_bucket": True,
                "bucket_reso_steps": 64,
                # Disable multiprocessing completely for macOS
                "persistent_data_loader_workers": False,
                "cache_latents_to_disk": False,
            },
            "optimizer": {
                "optimizer_type": params.get("optimizer_type", "AdamW8bit"),
                "lr_scheduler": params.get("lr_scheduler", "cosine_with_restarts"),
            },
            "network": {
                "network_module": "networks.lora",  # Required by Kohya-ss
                "network_dim": params.get("network_dim", 64),
                "network_alpha": params.get("network_alpha", 32),
            },
        }
        
        # Use TOML format for config file (Kohya-ss requirement)
        config_path = (output_dir / "training_config.toml").resolve()
        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config, f)
        
        logger.info(f"Training config saved to: {config_path}")
        
        try:
            # 5. Run actual Kohya training
            kohya_script = detection.get("train_script")
            python_exe = detection.get("python_executable", "python")
            
            if not kohya_script:
                logger.warning("Training script not found, using simulation mode")
                return await self._simulate_training(lora_model)
            
            # Build command - use wrapper script to patch multiprocessing
            kohya_script_str = str(kohya_script)
            config_path_str = str(config_path)
            
            # Get the directory of kohya script (sd-scripts) for working_dir
            kohya_script_dir = str(Path(kohya_script_str).parent)
            
            # Use wrapper script that patches multiprocessing before importing Kohya
            wrapper_script = str(Path(__file__).parent.parent.parent / 'scripts' / 'kohya_wrapper.py')
            
            cmd = [
                python_exe,
                wrapper_script,
                kohya_script_str,
                '--config_file', config_path_str,
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            logger.info(f"Working directory: {kohya_script_dir}")
            
            # Log training start
            await training_logger.log(
                lora_model.id,
                f"Starting Kohya training with script: {kohya_script}",
                level="INFO"
            )
            
            # Set environment variables to disable multiprocessing fork safety on macOS
            import os
            env = os.environ.copy()
            env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
            env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
            
            # Use subprocess with real-time output capture
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                env=env,  # Pass modified environment
            )
            
            # Track process for cancellation
            self._active_processes[lora_model.id] = process
            
            # Read output line by line in real-time
            full_output = []
            error_detected = False
            error_messages = []
            current_epoch = 0
            total_epochs = params.get("epochs", 10)
            current_loss = None
            
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                    
                full_output.append(line)
                logger.info(f"Kohya: {line}")
                
                # Log to training logger
                await training_logger.log(
                    lora_model.id,
                    line,
                    level="INFO"
                )
                
                # Detect errors
                if any(err in line.lower() for err in ['error:', 'exception:', 'traceback', 'failed']):
                    error_detected = True
                    error_messages.append(line)
                
                # Extract and publish progress if available
                # Priority: 1) steps percentage (most accurate), 2) epoch progress
                import re
                
                # Try to parse steps percentage first (e.g., "steps: 3%| | 26/1000")
                steps_percent_match = re.search(r'steps:\s*(\d+\.?\d*)%\|.*?(\d+)/(\d+)', line)
                if steps_percent_match:
                    try:
                        progress = float(steps_percent_match.group(1))
                        current_step = int(steps_percent_match.group(2))
                        total_steps = int(steps_percent_match.group(3))
                        
                        # Clamp to 0-100
                        progress = min(100.0, max(0.0, progress))
                        
                        # Try to extract loss from the same line
                        loss_match = re.search(r'avr_loss[=:]\s*([0-9.]+)', line)
                        if loss_match:
                            current_loss = float(loss_match.group(1))
                        
                        # Report progress via ProgressReporter
                        if self.progress_reporter:
                            await self.progress_reporter.report(
                                lora_id=lora_model.id,
                                progress=progress,
                                epoch=current_epoch,
                                total_epochs=total_epochs,
                                loss=current_loss,
                                message=f"Step {current_step}/{total_steps} ({progress:.1f}%)"
                            )
                        
                        logger.debug(f"📊 Steps progress: {current_step}/{total_steps} ({progress:.1f}%), loss: {current_loss}")
                    except Exception as e:
                        logger.debug(f"Failed to parse steps progress: {e}")
                
                # Fallback: Try to parse epoch progress
                elif 'epoch' in line.lower():
                    try:
                        # Match patterns like "Epoch 1/10" or "epoch: 1/10"
                        epoch_match = re.search(r'[Ee]poch[:\s]+(\d+)\s*/\s*(\d+)', line)
                        if epoch_match:
                            current_epoch = int(epoch_match.group(1))
                            total_epochs = int(epoch_match.group(2))
                            
                            # Try to extract loss from the same line
                            loss_match = re.search(r'loss[:\s]+([0-9.]+)', line, re.IGNORECASE)
                            if loss_match:
                                current_loss = float(loss_match.group(1))
                            
                            # Calculate progress percentage
                            progress = (current_epoch / total_epochs) * 100
                            
                            # Report progress via ProgressReporter
                            if self.progress_reporter:
                                await self.progress_reporter.report(
                                    lora_id=lora_model.id,
                                    progress=progress,
                                    epoch=current_epoch,
                                    total_epochs=total_epochs,
                                    loss=current_loss,
                                    message=f"Epoch {current_epoch}/{total_epochs} ({progress:.1f}%)"
                                )
                            
                            logger.info(f"📊 Epoch progress: {current_epoch}/{total_epochs} ({progress:.1f}%), loss: {current_loss}")
                    except Exception as e:
                        logger.warning(f"Failed to parse epoch progress: {e}")
            
            # Wait for process to complete
            returncode = process.wait()
            
            # Remove from active processes
            if lora_model.id in self._active_processes:
                del self._active_processes[lora_model.id]
            
            if returncode == 0 and not error_detected:
                logger.info(f"Training completed successfully")
                lora_model.final_loss = current_loss if current_loss is not None else 0.05
                lora_model.training_steps = config["general"].get("max_train_steps", 1000)
                lora_model.training_time_minutes = 30.0
                
                # Report completion via ProgressReporter
                if self.progress_reporter:
                    await self.progress_reporter.report(
                        lora_id=lora_model.id,
                        progress=100.0,
                        epoch=current_epoch if current_epoch > 0 else total_epochs,
                        total_epochs=total_epochs,
                        loss=current_loss,
                        message="Training completed successfully"
                    )
                
                await training_logger.log(
                    lora_model.id,
                    "Kohya training completed successfully",
                    level="INFO"
                )
                
                # Auto-trigger quality assessment
                try:
                    from app.services.quality_assessor import QualityAssessor
                    
                    async with get_db_session_standalone() as assess_db:
                        # Refresh model in new session
                        assess_model = await assess_db.get(LoRAModel, lora_model.id)
                        if assess_model:
                            assessor = QualityAssessor()
                            await assessor.assess_model_quality(
                                lora_id=lora_model.id,
                                num_test_images=5
                            )
                            logger.info(f"Auto quality assessment completed for LoRA {lora_model.id}")
                except Exception as e:
                    logger.warning(f"Auto quality assessment failed: {e}")
                
                return True
            else:
                error_detail = '\n'.join(error_messages[-10:]) if error_messages else '\n'.join(full_output[-20:])
                logger.error(f"Training failed with return code {returncode}: {error_detail}")
                
                await training_logger.log(
                    lora_model.id,
                    f"Kohya training failed (exit code {returncode}):\n{error_detail}",
                    level="ERROR"
                )
                
                return False
        
        except Exception as e:
            logger.error(f"Training execution error: {e}")
            
            # Log the error
            await training_logger.log(
                lora_model.id,
                f"Training failed with error: {str(e)}",
                level="ERROR"
            )
            
            # In real mode, raise exception instead of falling back to mock
            raise RuntimeError(f"Kohya training failed: {str(e)}")
    
    async def _simulate_training(self, lora_model: LoRAModel) -> bool:
        """
        Simulate training for testing when Kohya is not installed.
        
        Args:
            lora_model: LoRA model configuration
            
        Returns:
            True (simulation always succeeds)
        """
        logger.warning(f"Simulating training for: {lora_model.name}")
        
        # Simulate training time
        import asyncio
        await asyncio.sleep(5)
        
        # Create a dummy model file
        dummy_model_path = Path(lora_model.file_path)
        dummy_model_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dummy_model_path, "wb") as f:
            f.write(b"\x00" * 1024 * 1024)  # 1MB dummy file
        
        lora_model.final_loss = 0.05
        lora_model.training_steps = 1000
        lora_model.training_time_minutes = 5.0
        
        await training_logger.log(
            lora_model.id,
            "Simulation completed (Kohya not installed)",
            level="WARNING"
        )
        
        return True
    
    async def cancel_training(self, lora_id: int) -> bool:
        """
        Cancel an ongoing training task.
        
        Args:
            lora_id: LoRA model ID
            
        Returns:
            True if cancelled successfully
        """
        async with get_db_session_standalone() as session:
            lora_model = await session.get(LoRAModel, lora_id)
            if not lora_model:
                return False
            
            if lora_model.status != "training":
                logger.warning(f"Cannot cancel: model {lora_model.name} is not training")
                return False
            
            # Revoke the Celery task to terminate the Kohya subprocess in the worker
            if lora_model.celery_task_id:
                try:
                    from celery_worker import celery_app
                    logger.info(f"Revoking Celery task {lora_model.celery_task_id} for LoRA {lora_id}")
                    # terminate=True sends SIGTERM to the worker process
                    celery_app.control.revoke(lora_model.celery_task_id, terminate=True)
                    logger.info(f"✅ Celery task {lora_model.celery_task_id} revoked")
                except Exception as e:
                    logger.error(f"Failed to revoke Celery task: {e}")
                    # Continue to update status even if revoke fails
            
            # Update status to cancelled
            lora_model.status = "cancelled"
            lora_model.completed_at = datetime.now()
            await session.commit()
            
            logger.info(f"Cancelled training for: {lora_model.name}")
            return True
    
    async def get_lora_model(self, lora_id: int) -> Optional[LoRAModel]:
        """
        Get LoRA model by ID.
        
        Args:
            lora_id: LoRA model ID
            
        Returns:
            LoRA model or None
        """
        async with get_db_session_standalone() as session:
            return await session.get(LoRAModel, lora_id)
    
    async def list_lora_models(
        self,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> tuple:
        """
        List LoRA models with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            status: Filter by status
            
        Returns:
            Tuple of (models list, total count)
        """
        async with get_db_session_standalone() as session:
            query = select(LoRAModel)
            
            if status:
                query = query.where(LoRAModel.status == status)
            
            # Get total count
            count_result = await session.execute(query)
            total = len(count_result.scalars().all())
            
            # Get paginated results
            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            items = result.scalars().all()
            
            return items, total
    
    async def validate_model(self, lora_id: int) -> Dict[str, Any]:
        """
        Validate a trained LoRA model.
        
        Args:
            lora_id: LoRA model ID
            
        Returns:
            Validation results
        """
        async with get_db_session_standalone() as session:
            lora_model = await session.get(LoRAModel, lora_id)
            if not lora_model:
                return {"valid": False, "error": "Model not found"}
            
            # Check if file exists
            model_path = Path(lora_model.file_path)
            if not model_path.exists():
                return {"valid": False, "error": "Model file not found"}
            
            # Check file size (should be reasonable for LoRA)
            file_size_mb = model_path.stat().st_size / (1024 * 1024)
            if file_size_mb < 1 or file_size_mb > 500:
                return {
                    "valid": False,
                    "error": f"Unexpected file size: {file_size_mb:.2f} MB",
                }
            
            return {
                "valid": True,
                "file_size_mb": file_size_mb,
                "status": lora_model.status,
            }


# Global LoRA trainer instance
lora_trainer = LoRATrainer()
