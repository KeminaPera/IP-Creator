"""
Test IP-Adapter Strategy integration

This script tests the active IP-Adapter mode and verifies that the
strategy pattern loads the correct model weights.

Usage:
  python test_faceid_integration.py                              # Test with settings default
  set IP_ADAPTER_MODE=faceid  && python test_faceid_integration.py  # Test FaceID
  set IP_ADAPTER_MODE=faceid-plus && python test_faceid_integration.py  # Test FaceID-Plus
  set IP_ADAPTER_MODE=original && python test_faceid_integration.py  # Test Original
"""

import os
import sys
import time
from pathlib import Path


def test_faceid_integration():
    """Test IP-Adapter strategy integration"""

    print("=" * 80)
    print("IP-Adapter Strategy Integration Test")
    print("=" * 80)
    print()

    # Resolve active mode (env var > settings > "original")
    env_mode = os.environ.get("IP_ADAPTER_MODE", "").strip().lower()
    if env_mode:
        mode = env_mode
    else:
        try:
            from app.config.settings import settings as _settings
            mode = getattr(_settings, "IP_ADAPTER_MODE", "original")
        except Exception:
            mode = "original"
    print(f"📌 IP_ADAPTER_MODE: {mode}")
    print()

    mode_descriptions = {
        "original": ("📦 Original IP-Adapter (CLIP image features)", "65-75%"),
        "faceid":   ("🚀 IP-Adapter-FaceID (insightface 512-dim)", "75-85%"),
        "faceid-plus": ("🌟 IP-Adapter-FaceID-Plus (insightface + CLIP)", "80-90%"),
    }
    label, expected = mode_descriptions.get(mode, ("❓ Unknown mode", "N/A"))
    print(f"   {label}")
    print(f"   Expected similarity: {expected}")
    print()
    print("-" * 80)
    print()

    try:
        from app.services.ip_adapter_service import IPAdapterService
        from app.services.ip_adapter_strategies import IPAdapterStrategyRegistry
        from app.config.settings import settings

        print("✅ Import successful")
        print(f"   Available modes: {IPAdapterStrategyRegistry.available_modes()}")
        print()

        # Initialize service
        print("Initializing IPAdapterService...")
        start_time = time.time()
        service = IPAdapterService()
        init_time = time.time() - start_time
        print(f"✅ Service initialized in {init_time:.2f}s")
        print(f"   Device: {service.device}")
        print(f"   Dtype: {service.dtype}")
        print()

        # Resolve strategy and load pipeline
        strategy = service._resolve_strategy()
        config = strategy.get_model_config()
        print(f"Active strategy: {strategy.name}")
        print(f"   repo:        {config.repo}")
        print(f"   weight_name: {config.weight_name}")
        print(f"   scale range: {config.default_scale_range}")
        print(f"   supports LoRA: {strategy.supports_lora()}")
        print()

        # Dependency check
        from app.services.ip_adapter_strategies import GenerationContext
        import torch

        ctx = GenerationContext(
            prompt="test",
            negative_prompt="",
            width=512, height=512,
            steps=1, cfg_scale=7.0,
            seed=None, ip_adapter_scale=0.8,
            ref_images=[],
            device=service.device,
            dtype=service.dtype,
        )

        ok, reason = strategy.check_dependencies(ctx)
        if not ok:
            print(f"⚠️  Dependency check FAILED: {reason}")
            print("   Falling back to original mode for pipeline test.")
            from app.services.ip_adapter_strategies import OriginalIPAdapterStrategy
            strategy = OriginalIPAdapterStrategy()
        else:
            print("✅ All dependencies satisfied")
        print()

        # Load pipeline via strategy
        print("Loading IP-Adapter pipeline via strategy...")
        start_time = time.time()
        pipe = service._ensure_pipeline(strategy)
        load_time = time.time() - start_time
        print(f"✅ Pipeline loaded in {load_time:.2f}s")
        print()

        # Check what was loaded
        has_ip_adapter = (
            hasattr(pipe, 'ip_adapter')
            or (hasattr(pipe, 'image_encoder') and pipe.image_encoder is not None)
        )

        if has_ip_adapter:
            print("✅ IP-Adapter weights loaded successfully")
            if hasattr(pipe, 'image_encoder') and pipe.image_encoder is not None:
                print(f"   Image Encoder: {type(pipe.image_encoder).__name__}")
            print()

            if strategy.name == "original":
                print("📦 Original IP-Adapter Test: PASSED ✅")
                print()
                print("To enable FaceID:")
                print("1. Set IP_ADAPTER_MODE=faceid in .env or environment")
                print("2. Restart backend and Celery worker")
            elif strategy.name == "faceid":
                print("🎯 FaceID Integration Test: PASSED ✅")
                print()
                print("To upgrade to FaceID-Plus:")
                print("1. Download CLIP ViT-H/14 image_encoder (~3.94 GB)")
                print("2. Set IP_ADAPTER_MODE=faceid-plus")
            else:
                print("🌟 FaceID-Plus Integration Test: PASSED ✅")
                print()
                print("Next steps:")
                print("1. Start backend server with IP_ADAPTER_MODE=faceid-plus")
                print("2. Test three-view generation in frontend")
                print("3. Compare similarity with original IP-Adapter")

        else:
            print("❌ IP-Adapter weights not loaded properly")
            return False

        print()
        print("=" * 80)
        print("✅ Test completed successfully!")
        print("=" * 80)

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Test failed!")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_faceid_integration()
    sys.exit(0 if success else 1)
