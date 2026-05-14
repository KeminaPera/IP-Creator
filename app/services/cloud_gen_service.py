"""
Cloud Generation Service

HTTP client for calling cloud provider APIs for image/video generation.
Supports:
- Zhipu: CogView-3 (text-to-image), CogVideoX (text-to-video)
- OpenAI: DALL-E 3 (text-to-image)
- Dashscope: Wanx (text-to-image), Wan2.1 (text-to-video)
"""
import asyncio
import base64
import io
from typing import Dict, Any, Optional, List
import httpx

from app.utils.logger import logger


# Size mapping for different providers
SIZE_MAP = {
    "zhipu": {
        (512, 512): "512x512",
        (768, 768): "768x768",
        (1024, 1024): "1024x1024",
        (1024, 768): "1024x768",
        (768, 1024): "768x1024",
    },
    "openai": {
        (512, 512): "1024x1024",  # DALL-E 3 minimum is 1024
        (768, 768): "1024x1024",
        (1024, 1024): "1024x1024",
        (1024, 1792): "1024x1792",
        (1792, 1024): "1792x1024",
    },
    "dashscope": {
        # Dashscope native API uses * separator format
        (512, 512): "512*512",
        (768, 768): "768*768",
        (1024, 1024): "1024*1024",
        (720, 1280): "720*1280",
        (1280, 720): "1280*720",
    },
}


class CloudGenService:
    """
    Service for calling cloud provider image/video generation APIs.
    
    Each provider has different API patterns:
    - Zhipu: OpenAI-compatible /v4/images/generations endpoint
    - OpenAI: Standard /v1/images/generations endpoint
    - Dashscope: Custom /api/v1/services/aigc endpoint with task polling
    """

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy init of HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
    
    async def _update_channel_health_metrics(
        self,
        channel_id: int,
        status: str,
        response_time_ms: float
    ):
        """
        Update channel health metrics in database after each API call.
        Reuses the same logic as LLM manager's _update_health_metrics.
        
        Args:
            channel_id: LLMConfig ID (channel ID)
            status: "success" or "failure"
            response_time_ms: Response time in milliseconds
        """
        try:
            from app.config.database import async_session_factory
            from app.models.llm_model import LLMConfig
            from sqlalchemy import select
            from datetime import datetime
            
            async with async_session_factory() as session:
                # Get current config
                result = await session.execute(
                    select(LLMConfig).where(LLMConfig.id == channel_id)
                )
                config = result.scalar_one_or_none()
                
                if not config:
                    return
                
                # Update response time
                config.response_time_ms = response_time_ms
                
                # Update last call time
                config.last_health_check = datetime.now()
                
                # Update success rate using exponential moving average
                # This gives more weight to recent calls
                alpha = 0.1  # Learning rate (10% weight to new data)
                current_rate = config.success_rate or 100.0
                
                if status == "success":
                    new_rate = (alpha * 100.0) + ((1 - alpha) * current_rate)
                else:
                    new_rate = (alpha * 0.0) + ((1 - alpha) * current_rate)
                
                config.success_rate = new_rate
                
                # Update health status based on success rate
                if new_rate >= 80.0:
                    config.health_status = "healthy"
                elif new_rate >= 50.0:
                    config.health_status = "unhealthy"
                else:
                    config.health_status = "unhealthy"
                
                await session.commit()
                
                logger.info(f"Updated health metrics for channel {channel_id}: {status}, {response_time_ms:.0f}ms")
                
        except Exception as e:
            logger.error(f"Failed to update health metrics for channel {channel_id}: {e}")

    # ========== Image Generation ==========

    async def generate_image(
        self,
        provider: str,
        model_name: str,
        prompt: str,
        api_key: str,
        api_endpoint: str,
        width: int = 1024,
        height: int = 1024,
        channel_id: Optional[int] = None,  # Add channel_id for health metrics update
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate image via cloud API.
        
        Returns:
            Dict with 'image_bytes' (bytes) or 'image_url' (str), and 'status'
        """
        import time
        start_time = time.time()
        
        try:
            if provider == "zhipu":
                result = await self._generate_image_zhipu(
                    prompt, model_name, api_key, api_endpoint, width, height, **kwargs
                )
            elif provider == "openai":
                result = await self._generate_image_openai(
                    prompt, model_name, api_key, api_endpoint, width, height, **kwargs
                )
            elif provider == "dashscope":
                # Dashscope uses native API for image generation
                result = await self._generate_image_dashscope(
                    prompt, model_name, api_key, api_endpoint, width, height, **kwargs
                )
            else:
                result = {"status": "failed", "error": f"Unsupported image provider: {provider}"}
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Update health metrics if channel_id provided
            if channel_id:
                status = "success" if result.get("status") == "success" else "failure"
                await self._update_channel_health_metrics(channel_id, status, response_time_ms)
            
            return result
            
        except Exception as e:
            # Calculate failed response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Update health metrics if channel_id provided
            if channel_id:
                await self._update_channel_health_metrics(channel_id, "failure", response_time_ms)
            
            return {"status": "failed", "error": str(e)}

    async def _generate_image_zhipu(
        self,
        prompt: str,
        model_name: str,
        api_key: str,
        api_endpoint: str,
        width: int,
        height: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate image via Zhipu CogView API."""
        try:
            client = await self._get_client()
            size = self._get_size("zhipu", width, height)
            
            url = f"{api_endpoint}/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model_name,
                "prompt": prompt,
                "size": size,
            }
            
            logger.info(f"Zhipu CogView API call: model={model_name}, size={size}")
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            images = data.get("data", [])
            
            if not images:
                return {"status": "failed", "error": "No images returned from Zhipu API"}
            
            # Zhipu returns URL or base64
            image_data = images[0]
            image_url = image_data.get("url")
            b64_json = image_data.get("b64_json")
            
            if image_url:
                # Download the image
                img_response = await client.get(image_url)
                img_response.raise_for_status()
                return {"status": "success", "image_bytes": img_response.content}
            elif b64_json:
                image_bytes = base64.b64decode(b64_json)
                return {"status": "success", "image_bytes": image_bytes}
            else:
                return {"status": "failed", "error": "No image data in Zhipu API response"}
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except (AttributeError, ValueError):
                error_detail = "No error detail available"
            logger.error(f"Zhipu API HTTP error: {e.response.status_code} - {error_detail}")
            return {"status": "failed", "error": f"Zhipu API error ({e.response.status_code}): {error_detail}"}
        except Exception as e:
            logger.error(f"Zhipu CogView generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _generate_image_openai(
        self,
        prompt: str,
        model_name: str,
        api_key: str,
        api_endpoint: str,
        width: int,
        height: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate image via OpenAI DALL-E API (or any OpenAI-compatible API)."""
        return await self._generate_image_openai_compatible(
            prompt, model_name, api_key, api_endpoint, width, height, **kwargs
        )

    async def _generate_image_openai_compatible(
        self,
        prompt: str,
        model_name: str,
        api_key: str,
        api_endpoint: str,
        width: int,
        height: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate image via OpenAI-compatible API.
        Works with: OpenAI, Zhipu, Dashscope, DeepSeek, etc.
        """
        try:
            client = await self._get_client()
            size = self._get_size("openai", width, height)
            
            url = f"{api_endpoint}/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model_name,
                "prompt": prompt,
                "size": size,
                "n": 1,
                "response_format": "b64_json",
            }
            
            logger.info(f"OpenAI-compatible image API call: model={model_name}, size={size}")
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            images = data.get("data", [])
            
            if not images:
                return {"status": "failed", "error": "No images returned from API"}
            
            image_data = images[0]
            b64_json = image_data.get("b64_json")
            image_url = image_data.get("url")
            
            if b64_json:
                image_bytes = base64.b64decode(b64_json)
                return {"status": "success", "image_bytes": image_bytes}
            elif image_url:
                img_response = await client.get(image_url)
                img_response.raise_for_status()
                return {"status": "success", "image_bytes": img_response.content}
            else:
                return {"status": "failed", "error": "No image data in API response"}
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except (AttributeError, ValueError):
                error_detail = "No error detail available"
            logger.error(f"Image API HTTP error: {e.response.status_code} - {error_detail}")
            return {"status": "failed", "error": f"Image API error ({e.response.status_code}): {error_detail}"}
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _generate_image_dashscope(
        self,
        prompt: str,
        model_name: str,
        api_key: str,
        api_endpoint: str,
        width: int,
        height: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate image via Dashscope (Wanx) API with task polling."""
        try:
            client = await self._get_client()
            size = self._get_size("dashscope", width, height)
            
            # Submit task
            url = f"{api_endpoint}/api/v1/services/aigc/text2image/image-synthesis"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }
            body = {
                "model": model_name,
                "input": {"prompt": prompt},
                "parameters": {
                    "size": size,
                    "n": 1,
                },
            }
            
            logger.info(f"Dashscope Wanx API call: model={model_name}, size={size}")
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                return {"status": "failed", "error": f"No task_id from Dashscope API: {data}"}
            
            # Poll for result
            result = await self._poll_dashscope_task(client, api_key, api_endpoint, task_id)
            if result["status"] == "failed":
                return result
            
            # Download image from result URL
            image_url = result.get("image_url")
            if image_url:
                img_response = await client.get(image_url)
                img_response.raise_for_status()
                return {"status": "success", "image_bytes": img_response.content}
            else:
                return {"status": "failed", "error": "No image URL in Dashscope result"}
                
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except (AttributeError, ValueError):
                error_detail = "No error detail available"
            logger.error(f"Dashscope API HTTP error: {e.response.status_code} - {error_detail}")
            return {"status": "failed", "error": f"Dashscope API error ({e.response.status_code}): {error_detail}"}
        except Exception as e:
            logger.error(f"Dashscope Wanx generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ========== Video Generation ==========

    async def generate_video(
        self,
        provider: str,
        model_name: str,
        prompt: str,
        api_key: str,
        api_endpoint: str,
        image_url: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate video via cloud API.
        
        Returns:
            Dict with 'video_url' (str) or 'video_bytes' (bytes), and 'status'
        """
        if provider == "zhipu":
            return await self._generate_video_zhipu(
                prompt, model_name, api_key, api_endpoint, image_url, **kwargs
            )
        elif provider == "dashscope":
            return await self._generate_video_dashscope(
                prompt, model_name, api_key, api_endpoint, image_url, **kwargs
            )
        else:
            return {"status": "failed", "error": f"Unsupported video provider: {provider}"}

    async def _generate_video_zhipu(
        self,
        prompt: str,
        model_name: str,
        api_key: str,
        api_endpoint: str,
        image_url: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate video via Zhipu CogVideoX API with task polling."""
        try:
            client = await self._get_client()
            
            url = f"{api_endpoint}/videos/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model_name,
                "prompt": prompt,
            }
            if image_url:
                body["image_url"] = image_url
            
            logger.info(f"Zhipu CogVideoX API call: model={model_name}")
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            task_id = data.get("id") or data.get("task_id")
            
            if not task_id:
                # Check if result is immediate
                video_url = data.get("data", {}).get("url") or data.get("url")
                if video_url:
                    vid_response = await client.get(video_url)
                    vid_response.raise_for_status()
                    return {"status": "success", "video_bytes": vid_response.content}
                return {"status": "failed", "error": f"No task_id or result from Zhipu video API: {data}"}
            
            # Poll for result
            result = await self._poll_zhipu_video_task(client, api_key, api_endpoint, task_id)
            return result
            
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except (AttributeError, ValueError):
                error_detail = "No error detail available"
            logger.error(f"Zhipu Video API HTTP error: {e.response.status_code} - {error_detail}")
            return {"status": "failed", "error": f"Zhipu Video API error ({e.response.status_code}): {error_detail}"}
        except Exception as e:
            logger.error(f"Zhipu CogVideoX generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _generate_video_dashscope(
        self,
        prompt: str,
        model_name: str,
        api_key: str,
        api_endpoint: str,
        image_url: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate video via Dashscope (Wan2.1) API with task polling."""
        try:
            client = await self._get_client()
            
            url = f"{api_endpoint}/api/v1/services/aigc/text2video/video-synthesis"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable",
            }
            body = {
                "model": model_name,
                "input": {
                    "prompt": prompt,
                },
                "parameters": {},
            }
            if image_url:
                body["input"]["img_url"] = image_url
            
            logger.info(f"Dashscope Wan2.1 API call: model={model_name}")
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                return {"status": "failed", "error": f"No task_id from Dashscope video API: {data}"}
            
            # Poll for result
            result = await self._poll_dashscope_task(client, api_key, api_endpoint, task_id, is_video=True)
            return result
            
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except (AttributeError, ValueError):
                error_detail = "No error detail available"
            logger.error(f"Dashscope Video API HTTP error: {e.response.status_code} - {error_detail}")
            return {"status": "failed", "error": f"Dashscope Video API error ({e.response.status_code}): {error_detail}"}
        except Exception as e:
            logger.error(f"Dashscope Wan2.1 generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ========== Task Polling ==========

    async def _poll_zhipu_video_task(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        api_endpoint: str,
        task_id: str,
        max_wait: int = 300,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Poll Zhipu video task until complete."""
        url = f"{api_endpoint}/videos/result/{task_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        elapsed = 0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                task_status = data.get("task_status", data.get("status", ""))
                if task_status == "SUCCESS" or task_status == "succeeded":
                    video_url = data.get("data", {}).get("url") or data.get("url")
                    if video_url:
                        vid_response = await client.get(video_url)
                        vid_response.raise_for_status()
                        return {"status": "success", "video_bytes": vid_response.content}
                    return {"status": "failed", "error": "No video URL in Zhipu result"}
                elif task_status in ("FAIL", "failed"):
                    error_msg = data.get("message", "Unknown error")
                    return {"status": "failed", "error": f"Zhipu video task failed: {error_msg}"}
                # Still processing, continue polling
                logger.info(f"Zhipu video task {task_id}: {task_status}, polling... ({elapsed}s)")
            except Exception as e:
                logger.warning(f"Error polling Zhipu task {task_id}: {e}")
        
        return {"status": "failed", "error": f"Zhipu video task timed out after {max_wait}s"}

    async def _poll_dashscope_task(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        api_endpoint: str,
        task_id: str,
        is_video: bool = False,
        max_wait: int = 300,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Poll Dashscope task until complete."""
        url = f"{api_endpoint}/api/v1/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        elapsed = 0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                task_status = data.get("output", {}).get("task_status", "")
                if task_status == "SUCCEEDED":
                    results = data.get("output", {}).get("results", [])
                    if results:
                        result_url = results[0].get("url")
                        if is_video:
                            return {"status": "success", "video_url": result_url}
                        else:
                            return {"status": "success", "image_url": result_url}
                    return {"status": "failed", "error": "No results in Dashscope task output"}
                elif task_status == "FAILED":
                    error_msg = data.get("output", {}).get("message", "Unknown error")
                    return {"status": "failed", "error": f"Dashscope task failed: {error_msg}"}
                # Still processing
                logger.info(f"Dashscope task {task_id}: {task_status}, polling... ({elapsed}s)")
            except Exception as e:
                logger.warning(f"Error polling Dashscope task {task_id}: {e}")
        
        return {"status": "failed", "error": f"Dashscope task timed out after {max_wait}s"}

    # ========== Utility ==========

    def _get_size(self, provider: str, width: int, height: int) -> str:
        """Get provider-specific size string from width/height."""
        size_map = SIZE_MAP.get(provider, {})
        size_str = size_map.get((width, height))
        if size_str:
            return size_str
        
        # Fallback: find closest available size
        if provider == "dashscope":
            return f"{width}*{height}"
        else:
            return f"{width}x{height}"


# Global service instance
cloud_gen_service = CloudGenService()
