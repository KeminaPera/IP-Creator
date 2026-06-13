"""
FlowPipe Built-in Nodes

Importing this module registers all built-in nodes with the NodeRegistry.
Also provides the default three-view generation workflow.
"""

# Import all node modules to trigger @register_node decorators
from flowpipe.nodes.model_loader import SDModelLoaderNode
from flowpipe.nodes.face_detect import FaceDetectNode
from flowpipe.nodes.image_preproc import ImagePreprocNode
from flowpipe.nodes.prompt_builder import PromptBuilderNode
from flowpipe.nodes.ip_adapter_embed import IPAdapterEmbedNode
from flowpipe.nodes.lora_loader import LoRALoaderNode
from flowpipe.nodes.diffusion_sampler import DiffusionSamplerNode
from flowpipe.nodes.image_save import ImageSaveNode
from flowpipe.nodes.llm_text import LLMTextNode
from flowpipe.nodes.cloud_image import CloudImageNode
from flowpipe.nodes.cloud_video import CloudVideoNode


# Default three-view generation workflow definition
DEFAULT_THREE_VIEW_WORKFLOW = {
    "name": "Three-View Generation (FaceID-Plus SD1.5)",
    "version": "1.0",
    "nodes": [
        {
            "id": "model_loader",
            "type": "SDModelLoader",
            "position": {"x": 50, "y": 200},
            "parameters": {
                "model_id": "runwayml/stable-diffusion-v1-5",
                "scheduler": "dpmsolver++_karras",
                "dtype": "float16",
            },
        },
        {
            "id": "face_detect",
            "type": "FaceDetect",
            "position": {"x": 50, "y": 450},
            "parameters": {
                "model_name": "buffalo_l",
                "det_size": "640",
            },
        },
        {
            "id": "image_preproc",
            "type": "ImagePreproc",
            "position": {"x": 350, "y": 450},
            "parameters": {
                "target_size": 512,
                "mode": "face_aware_crop",
                "padding_factor": 1.5,
            },
        },
        {
            "id": "prompt_builder",
            "type": "PromptBuilder",
            "position": {"x": 350, "y": 50},
            "parameters": {
                "trigger_word": "character",
                "view_type": "front",
                "prompt_template": "",
                "negative_prompt": (
                    "ugly, deformed, text, "
                    "asymmetric eyes, deformed pupils, deformed mouth, "
                    "extra fingers, mutated hands, bad anatomy, "
                    "blurry face, distorted facial features"
                ),
            },
        },
        {
            "id": "ip_adapter_embed",
            "type": "IPAdapterEmbed",
            "position": {"x": 650, "y": 300},
            "parameters": {
                "mode": "faceid-plus",
                "ip_adapter_scale": 0.93,
            },
        },
        {
            "id": "sampler",
            "type": "DiffusionSampler",
            "position": {"x": 950, "y": 200},
            "parameters": {
                "steps": 30,
                "cfg_scale": 5.5,
                "width": 512,
                "height": 512,
                "seed": 0,
            },
        },
        {
            "id": "image_save",
            "type": "ImageSave",
            "position": {"x": 1250, "y": 200},
            "parameters": {
                "format": "PNG",
            },
        },
    ],
    "edges": [
        # Note: face_detect.image and image_preproc.image are runtime-injected
        # (declared with "runtime": True in INPUT_TYPES, no edge needed).
        # Model -> IP-Adapter Embed & Sampler
        {"source": "model_loader", "source_output": "pipe", "target": "ip_adapter_embed", "target_input": "pipe"},
        {"source": "model_loader", "source_output": "pipe", "target": "sampler", "target_input": "pipe"},
        # Face Detect -> Image Preproc & IP-Adapter Embed
        {"source": "face_detect", "source_output": "bbox", "target": "image_preproc", "target_input": "bbox"},
        {"source": "face_detect", "source_output": "faces", "target": "ip_adapter_embed", "target_input": "faces"},
        # Image Preproc -> IP-Adapter Embed
        {"source": "image_preproc", "source_output": "images", "target": "ip_adapter_embed", "target_input": "images"},
        # Prompt Builder -> Sampler
        {"source": "prompt_builder", "source_output": "prompt", "target": "sampler", "target_input": "prompt"},
        {"source": "prompt_builder", "source_output": "neg_prompt", "target": "sampler", "target_input": "neg_prompt"},
        # IP-Adapter Embed -> Sampler
        {"source": "ip_adapter_embed", "source_output": "pipe", "target": "sampler", "target_input": "pipe"},
        {"source": "ip_adapter_embed", "source_output": "embeddings", "target": "sampler", "target_input": "embeddings"},
        # Sampler -> Image Save
        {"source": "sampler", "source_output": "image", "target": "image_save", "target_input": "image"},
    ],
    "metadata": {
        "description": "Default three-view generation workflow using IP-Adapter FaceID-Plus with SD 1.5",
        "template_key": "three_view",
        "content_type": "image",
        "author": "flowpipe",
    },
}

STORY_GENERATION_WORKFLOW = {
    "name": "Story Generation (LLM)",
    "version": "1.0",
    "nodes": [
        {
            "id": "llm_text",
            "type": "LLMText",
            "position": {"x": 200, "y": 200},
            "parameters": {
                "prompt": "",
                "channel_id": 0,
                "style": "healing",
                "temperature": 0.8,
                "max_tokens": 2048,
            },
        },
    ],
    "edges": [],
    "metadata": {
        "description": "Generate story/script using LLM models",
        "template_key": "story",
        "content_type": "story",
        "author": "flowpipe",
    },
}

CLOUD_IMAGE_WORKFLOW = {
    "name": "Cloud Image Generation",
    "version": "1.0",
    "nodes": [
        {
            "id": "cloud_image",
            "type": "CloudImage",
            "position": {"x": 200, "y": 200},
            "parameters": {
                "prompt": "",
                "channel_id": 0,
                "width": 1024,
                "height": 1024,
                "negative_prompt": "",
            },
        },
    ],
    "edges": [],
    "metadata": {
        "description": "Generate images via cloud API (Zhipu/DALL-E/Dashscope)",
        "template_key": "cloud_image",
        "content_type": "image",
        "author": "flowpipe",
    },
}

CLOUD_VIDEO_WORKFLOW = {
    "name": "Cloud Video Generation",
    "version": "1.0",
    "nodes": [
        {
            "id": "cloud_video",
            "type": "CloudVideo",
            "position": {"x": 200, "y": 200},
            "parameters": {
                "prompt": "",
                "channel_id": 0,
                "duration_seconds": 5,
                "fps": 24,
                "width": 512,
                "height": 512,
            },
        },
    ],
    "edges": [],
    "metadata": {
        "description": "Generate videos via cloud API (Zhipu CogVideoX / Dashscope)",
        "template_key": "cloud_video",
        "content_type": "video",
        "author": "flowpipe",
    },
}

# All built-in workflow templates
BUILTIN_WORKFLOW_TEMPLATES = [
    DEFAULT_THREE_VIEW_WORKFLOW,
    STORY_GENERATION_WORKFLOW,
    CLOUD_IMAGE_WORKFLOW,
    CLOUD_VIDEO_WORKFLOW,
]

__all__ = [
    "SDModelLoaderNode",
    "FaceDetectNode",
    "ImagePreprocNode",
    "PromptBuilderNode",
    "IPAdapterEmbedNode",
    "LoRALoaderNode",
    "DiffusionSamplerNode",
    "ImageSaveNode",
    "LLMTextNode",
    "CloudImageNode",
    "CloudVideoNode",
    "DEFAULT_THREE_VIEW_WORKFLOW",
    "STORY_GENERATION_WORKFLOW",
    "CLOUD_IMAGE_WORKFLOW",
    "CLOUD_VIDEO_WORKFLOW",
    "BUILTIN_WORKFLOW_TEMPLATES",
]
