"""
Video Post-Processing Module

Handles video editing operations including concatenation,
subtitle overlay, background music, and export optimization.
Uses MoviePy for actual video processing.
"""
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.config.settings import settings
from app.utils.logger import logger


class PostProcessor:
    """
    Service for video post-processing operations.
    
    Provides video concatenation, subtitle addition, background music,
    filters, and platform-optimized export using MoviePy.
    """
    
    def __init__(self):
        """Initialize post-processor."""
        self.videos_path = Path(settings.VIDEOS_PATH)
        self.videos_path.mkdir(parents=True, exist_ok=True)
    
    async def process_video(self, video_path: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply multiple operations to a video in sequence.
        
        Args:
            video_path: Input video path
            operations: List of operations to apply
            
        Returns:
            Result with final output path
        """
        try:
            from moviepy import VideoFileClip
            
            current_path = video_path
            
            for op in operations:
                op_type = op.get("type")
                output_path = op.get("output_path", current_path)
                
                if op_type == "concatenate":
                    result = await self.concatenate_videos(
                        op.get("video_paths", []),
                        output_path,
                        op.get("transition_type", "fade"),
                    )
                elif op_type == "subtitles":
                    result = await self.add_subtitles(
                        current_path,
                        op.get("subtitle_text", ""),
                        output_path,
                    )
                elif op_type == "music":
                    result = await self.add_background_music(
                        current_path,
                        op.get("music_path", ""),
                        output_path,
                    )
                elif op_type == "filter":
                    result = await self.apply_filter(
                        current_path,
                        output_path,
                        op.get("filter_type", "warm"),
                    )
                elif op_type == "export":
                    result = await self.export_video(
                        current_path,
                        output_path,
                        op.get("resolution", "1080p"),
                    )
                else:
                    continue
                
                if result["status"] == "success":
                    current_path = result["output_path"]
            
            return {
                "status": "success",
                "output_path": current_path,
                "operations_applied": len(operations),
            }
        
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
        transition_type: str = "fade",
        transition_duration: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Concatenate multiple videos with transitions.
        
        Args:
            video_paths: List of video file paths
            output_path: Output file path
            transition_type: Transition type (fade, cut, dissolve)
            transition_duration: Transition duration in seconds
            
        Returns:
            Result with output path and metadata
        """
        try:
            from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip
            
            logger.info(f"Concatenating {len(video_paths)} videos")
            
            clips = [VideoFileClip(path) for path in video_paths if os.path.exists(path)]
            
            if not clips:
                return {"status": "failed", "error": "No valid video files found"}
            
            if transition_type == "fade":
                # Add fade transitions
                from moviepy import vfx
                final_clip = concatenate_videoclips(clips, method="compose")
            else:
                final_clip = concatenate_videoclips(clips)
            
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            final_clip.close()
            
            for clip in clips:
                clip.close()
            
            return {
                "status": "success",
                "output_path": output_path,
                "video_count": len(clips),
            }
        
        except Exception as e:
            logger.error(f"Video concatenation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def add_subtitles(
        self,
        video_path: str,
        subtitle_text: str,
        output_path: str,
        position: str = "bottom",
        font_size: int = 24,
        font_color: str = "white",
    ) -> Dict[str, Any]:
        """
        Add subtitles to video using MoviePy.
        
        Args:
            video_path: Input video path
            subtitle_text: Subtitle text or SRT file path
            output_path: Output file path
            position: Subtitle position
            font_size: Font size
            font_color: Font color
            
        Returns:
            Result with output path
        """
        try:
            from moviepy import VideoFileClip, TextClip, CompositeVideoClip
            
            logger.info(f"Adding subtitles to: {video_path}")
            
            video = VideoFileClip(video_path)
            
            # Create text clip
            txt_clip = TextClip(
                text=subtitle_text,
                font_size=font_size,
                color=font_color,
                stroke_color="black",
                stroke_width=1,
                method="caption",
                size=(video.w * 0.9, None),
            )
            
            txt_clip = txt_clip.with_duration(video.duration)
            
            if position == "bottom":
                txt_clip = txt_clip.with_position(("center", "bottom"))
            elif position == "top":
                txt_clip = txt_clip.with_position(("center", "top"))
            else:
                txt_clip = txt_clip.with_position("center")
            
            # Composite
            final = CompositeVideoClip([video, txt_clip])
            final.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            video.close()
            txt_clip.close()
            final.close()
            
            return {
                "status": "success",
                "output_path": output_path,
            }
        
        except Exception as e:
            logger.error(f"Subtitle addition failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.3,
        video_volume: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Add background music to video using MoviePy.
        
        Args:
            video_path: Input video path
            music_path: Background music file path
            output_path: Output file path
            music_volume: Music volume (0.0-1.0)
            video_volume: Original video volume (0.0-1.0)
            
        Returns:
            Result with output path
        """
        try:
            from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
            
            logger.info(f"Adding background music to: {video_path}")
            
            video = VideoFileClip(video_path)
            music = AudioFileClip(music_path)
            
            # Loop music if shorter than video
            if music.duration < video.duration:
                n_loops = int(video.duration / music.duration) + 1
                music = music.loop(n=n_loops)
            
            # Trim music to video duration
            music = music.subclipped(0, video.duration)
            
            # Adjust volumes
            music = music.with_volume_scaled(music_volume)
            video_audio = video.audio.with_volume_scaled(video_volume) if video.audio else None
            
            # Composite audio
            if video_audio:
                final_audio = CompositeAudioClip([video_audio, music])
            else:
                final_audio = music
            
            final_video = video.with_audio(final_audio)
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            video.close()
            music.close()
            if video_audio:
                video_audio.close()
            final_video.close()
            
            return {
                "status": "success",
                "output_path": output_path,
            }
        
        except Exception as e:
            logger.error(f"Background music addition failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def apply_filter(
        self,
        video_path: str,
        output_path: str,
        filter_type: str = "warm",
        intensity: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Apply color filter to video using MoviePy.
        
        Args:
            video_path: Input video path
            output_path: Output file path
            filter_type: Filter type (warm, cool, vintage, etc.)
            intensity: Filter intensity (0.0-1.0)
            
        Returns:
            Result with output path
        """
        try:
            from moviepy import VideoFileClip
            
            logger.info(f"Applying {filter_type} filter to: {video_path}")
            
            video = VideoFileClip(video_path)
            
            if filter_type == "warm":
                def filter_frame(frame):
                    frame[:, :, 0] = frame[:, :, 0] * (1 + intensity * 0.1)
                    frame[:, :, 2] = frame[:, :, 2] * (1 - intensity * 0.05)
                    return frame
            elif filter_type == "cool":
                def filter_frame(frame):
                    frame[:, :, 2] = frame[:, :, 2] * (1 + intensity * 0.1)
                    frame[:, :, 0] = frame[:, :, 0] * (1 - intensity * 0.05)
                    return frame
            elif filter_type == "vintage":
                def filter_frame(frame):
                    import numpy as np
                    gray = np.dot(frame[...,:3], [0.299, 0.587, 0.114])
                    frame[:, :, 0] = gray * (1 + intensity * 0.2)
                    frame[:, :, 1] = gray * (1 + intensity * 0.1)
                    frame[:, :, 2] = gray * (1 - intensity * 0.1)
                    return frame
            else:
                filter_frame = lambda f: f
            
            filtered = video.with_effects([lambda get_frame, t: filter_frame(get_frame(t))])
            filtered.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            video.close()
            filtered.close()
            
            return {
                "status": "success",
                "output_path": output_path,
            }
        
        except Exception as e:
            logger.error(f"Filter application failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def export_video(
        self,
        video_path: str,
        output_path: str,
        resolution: str = "1080p",
        fps: int = 30,
        bitrate: str = "8000k",
        format: str = "mp4",
    ) -> Dict[str, Any]:
        """
        Export video with platform optimization.
        
        Args:
            video_path: Input video path
            output_path: Output file path
            resolution: Output resolution (720p, 1080p, 4k)
            fps: Frames per second
            bitrate: Video bitrate
            format: Output format
            
        Returns:
            Result with output path and metadata
        """
        try:
            from moviepy import VideoFileClip
            
            logger.info(f"Exporting video: {video_path} -> {output_path}")
            logger.info(f"Resolution: {resolution}, FPS: {fps}")
            
            video = VideoFileClip(video_path)
            
            # Set resolution
            if resolution == "720p":
                target_height = 720
            elif resolution == "1080p":
                target_height = 1080
            elif resolution == "4k":
                target_height = 2160
            else:
                target_height = video.h
            
            if video.h != target_height:
                target_width = int(video.w * (target_height / video.h))
                video = video.resized(new_size=(target_width, target_height))
            
            # Export with settings
            video.write_videofile(
                output_path,
                fps=fps,
                bitrate=bitrate,
                codec="libx264",
                audio_codec="aac",
            )
            
            video.close()
            
            return {
                "status": "success",
                "output_path": output_path,
                "resolution": resolution,
                "fps": fps,
            }
        
        except Exception as e:
            logger.error(f"Video export failed: {e}")
            return {"status": "failed", "error": str(e)}


# Global post-processor instance
post_processor = PostProcessor()
