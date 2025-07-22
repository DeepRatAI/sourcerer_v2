import asyncio
import uuid
import httpx
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..models.source import SourceItem
from ..models.content import (
    GeneratedContent, ContentType, PlatformScript, GeneratedImage,
    ResearchDocument
)
from ..config.paths import get_outputs_dir
from ..utils.file_utils import ensure_directory
from ..utils.logging import get_logger
from ..providers import get_provider_adapter
from ..config import ConfigManager


class BaseGenerator:
    """Base class for content generators"""
    
    def __init__(self):
        self.logger = get_logger(f"sourcerer.generation.{self.__class__.__name__.lower()}")
        self.config_manager = ConfigManager()
        self.outputs_dir = get_outputs_dir()
        ensure_directory(self.outputs_dir)
    
    async def _get_llm_response(self, 
                              messages: List[Dict[str, str]],
                              max_tokens: int = 1000,
                              temperature: float = 0.7) -> str:
        """Get response from active LLM provider"""
        
        try:
            if not self.config_manager.config.active_provider:
                raise ValueError("No active provider configured")
            
            provider_config = self.config_manager.config.providers[self.config_manager.config.active_provider]
            api_key = self.config_manager.get_provider_api_key(self.config_manager.config.active_provider)
            adapter = get_provider_adapter(self.config_manager.config.active_provider, provider_config, api_key)
            
            response = await adapter.chat(
                messages=messages,
                model=self.config_manager.config.active_model,
                params={
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                stream=False
            )
            
            return response.content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to get LLM response: {e}")
            raise


class SummaryGenerator(BaseGenerator):
    """Generates comprehensive summaries with insights"""
    
    async def generate_summary(self,
                             item: SourceItem,
                             research: Optional[ResearchDocument] = None,
                             custom_instructions: Optional[str] = None) -> GeneratedContent:
        """Generate a comprehensive summary"""
        
        try:
            self.logger.info(f"Generating summary for: {item.title}")
            
            # Build context
            context_parts = [
                f"Article Title: {item.title}",
                f"Source URL: {item.url}",
            ]
            
            if item.author:
                context_parts.append(f"Author: {item.author}")
            
            if item.published_at:
                context_parts.append(f"Published: {item.published_at.strftime('%Y-%m-%d')}")
            
            if item.summary:
                context_parts.append(f"Original Summary: {item.summary}")
            
            if item.content:
                content_preview = item.content[:2000] if len(item.content) > 2000 else item.content
                context_parts.append(f"Article Content: {content_preview}")
            
            # Add research context
            if research and research.summary:
                context_parts.append(f"Research Context: {research.summary}")
            
            # Create generation prompt
            prompt = f"""Create a comprehensive summary and analysis of the following article. Include key insights, potential implications, and analysis of trends or patterns mentioned.

{chr(10).join(context_parts)}

Tags: {', '.join(item.tags) if item.tags else 'None'}

Your summary should include:
1. Core Summary: Key points and main message
2. Key Insights: Important takeaways and implications  
3. Context & Background: Relevant background information
4. Trends & Patterns: Notable trends or patterns identified
5. Potential Impact: Possible implications or effects

"""
            
            if custom_instructions:
                prompt += f"\nCustom Instructions: {custom_instructions}\n"
            
            prompt += "Provide a well-structured, informative summary:"
            
            # Generate summary
            messages = [{"role": "user", "content": prompt}]
            summary_content = await self._get_llm_response(
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )
            
            # Create content object
            generated_content = GeneratedContent(
                type=ContentType.SUMMARY,
                title=f"Summary: {item.title}",
                content=summary_content,
                metadata={
                    'source_item_id': item.id,
                    'source_title': item.title,
                    'source_url': item.url,
                    'has_research': research is not None,
                    'custom_instructions': custom_instructions,
                    'word_count': len(summary_content.split())
                }
            )
            
            self.logger.info("Summary generation completed")
            return generated_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            raise


class ScriptGenerator(BaseGenerator):
    """Generates platform-specific scripts"""
    
    PLATFORM_SPECS = {
        'tiktok': {
            'max_duration': 60,
            'style': 'engaging, trendy, hook-focused',
            'length': 'short and punchy',
            'tone': 'casual, energetic'
        },
        'instagram': {
            'max_duration': 90,
            'style': 'visual-focused, story-driven',
            'length': 'concise with strong visuals',
            'tone': 'authentic, relatable'
        },
        'x': {
            'max_chars': 280,
            'style': 'conversational, thread-friendly',
            'length': 'thread of 3-5 tweets',
            'tone': 'informative, engaging'
        },
        'youtube': {
            'max_duration': 300,
            'style': 'educational, comprehensive',
            'length': 'detailed explanation',
            'tone': 'professional, informative'
        }
    }
    
    async def generate_scripts(self,
                             item: SourceItem,
                             platforms: List[str],
                             research: Optional[ResearchDocument] = None,
                             custom_instructions: Optional[str] = None) -> GeneratedContent:
        """Generate scripts for multiple platforms"""
        
        try:
            self.logger.info(f"Generating scripts for platforms: {platforms}")
            
            scripts = []
            
            # Generate script for each platform
            for platform in platforms:
                if platform not in self.PLATFORM_SPECS:
                    self.logger.warning(f"Unknown platform: {platform}")
                    continue
                
                script_content = await self._generate_platform_script(
                    item=item,
                    platform=platform,
                    research=research,
                    custom_instructions=custom_instructions
                )
                
                scripts.append(PlatformScript(
                    platform=platform,
                    content=script_content,
                    metadata={
                        'spec': self.PLATFORM_SPECS[platform],
                        'generated_at': datetime.now().isoformat()
                    }
                ))
            
            generated_content = GeneratedContent(
                type=ContentType.SCRIPTS,
                title=f"Scripts for {item.title}",
                scripts=scripts,
                metadata={
                    'source_item_id': item.id,
                    'platforms': platforms,
                    'has_research': research is not None,
                    'custom_instructions': custom_instructions
                }
            )
            
            self.logger.info(f"Generated scripts for {len(scripts)} platforms")
            return generated_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate scripts: {e}")
            raise
    
    async def _generate_platform_script(self,
                                      item: SourceItem,
                                      platform: str,
                                      research: Optional[ResearchDocument] = None,
                                      custom_instructions: Optional[str] = None) -> str:
        """Generate script for specific platform"""
        
        spec = self.PLATFORM_SPECS[platform]
        
        # Build context
        context = f"""Article: {item.title}
Content Preview: {(item.content or item.summary or '')[:1000]}
URL: {item.url}"""
        
        if research and research.summary:
            context += f"\nResearch Insights: {research.summary[:500]}"
        
        # Create platform-specific prompt
        prompt = f"""Create a {platform} script based on this article.

{context}

Platform Requirements for {platform.upper()}:
- Style: {spec['style']}
- Length: {spec['length']}  
- Tone: {spec['tone']}
"""
        
        if platform == 'x':
            prompt += f"- Character limit: {spec['max_chars']} per tweet\n"
            prompt += "Format as a Twitter thread with numbered tweets.\n"
        elif platform in ['tiktok', 'instagram', 'youtube']:
            prompt += f"- Max duration: {spec['max_duration']} seconds\n"
            prompt += "Include timing cues and visual descriptions.\n"
        
        if custom_instructions:
            prompt += f"\nCustom Instructions: {custom_instructions}\n"
        
        prompt += f"\nCreate an engaging {platform} script:"
        
        messages = [{"role": "user", "content": prompt}]
        return await self._get_llm_response(
            messages=messages,
            max_tokens=600 if platform == 'x' else 800,
            temperature=0.8
        )


class ImageGenerator(BaseGenerator):
    """Generates images using OpenAI DALL-E"""
    
    def __init__(self):
        super().__init__()
        self.semaphore = asyncio.Semaphore(2)  # Limit concurrent image requests
        self.images_dir = self.outputs_dir / "images"
        ensure_directory(self.images_dir)
    
    async def generate_images(self,
                            item: SourceItem,
                            image_count: int = 1,
                            research: Optional[ResearchDocument] = None,
                            custom_instructions: Optional[str] = None) -> GeneratedContent:
        """Generate images for content"""
        
        try:
            # Check if image generation is enabled
            if not self.config_manager.config.image_generation.enabled:
                raise ValueError("Image generation is not enabled")
            
            # Check if OpenAI provider is available
            if 'openai' not in self.config_manager.config.providers:
                raise ValueError("OpenAI provider required for image generation")
            
            self.logger.info(f"Generating {image_count} images for: {item.title}")
            
            # Generate image prompts
            image_prompts = await self._generate_image_prompts(
                item=item,
                count=image_count,
                research=research,
                custom_instructions=custom_instructions
            )
            
            # Generate images concurrently
            tasks = []
            for i, prompt in enumerate(image_prompts):
                task = self._generate_single_image(
                    prompt=prompt,
                    item_id=item.id,
                    image_index=i
                )
                tasks.append(task)
            
            # Wait for all images to generate
            generated_images = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful generations
            successful_images = []
            for result in generated_images:
                if isinstance(result, GeneratedImage):
                    successful_images.append(result)
                else:
                    self.logger.error(f"Image generation failed: {result}")
            
            generated_content = GeneratedContent(
                type=ContentType.IMAGES,
                title=f"Images for {item.title}",
                images=successful_images,
                metadata={
                    'source_item_id': item.id,
                    'requested_count': image_count,
                    'successful_count': len(successful_images),
                    'has_research': research is not None,
                    'custom_instructions': custom_instructions
                }
            )
            
            self.logger.info(f"Generated {len(successful_images)}/{image_count} images successfully")
            return generated_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate images: {e}")
            raise
    
    async def _generate_image_prompts(self,
                                    item: SourceItem,
                                    count: int,
                                    research: Optional[ResearchDocument] = None,
                                    custom_instructions: Optional[str] = None) -> List[str]:
        """Generate image prompts using LLM"""
        
        # Build context
        context = f"""Article: {item.title}
Content: {(item.content or item.summary or '')[:1500]}"""
        
        if research and research.summary:
            context += f"\nResearch Context: {research.summary[:500]}"
        
        prompt = f"""Based on this article, create {count} detailed image generation prompt(s) that would create compelling visual content.

{context}

The image prompt(s) should:
- Be visually engaging and relevant to the content
- Include specific visual elements, style, and composition
- Be suitable for social media and content marketing
- Avoid text or specific people/brands
- Be detailed enough for AI image generation

"""
        
        if custom_instructions:
            prompt += f"Custom Requirements: {custom_instructions}\n"
        
        if count == 1:
            prompt += "Generate one detailed image prompt:"
        else:
            prompt += f"Generate {count} different image prompts, numbered 1-{count}:"
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._get_llm_response(
            messages=messages,
            max_tokens=400,
            temperature=0.8
        )
        
        # Parse prompts from response
        if count == 1:
            return [response.strip()]
        else:
            return self._parse_multiple_prompts(response, count)
    
    def _parse_multiple_prompts(self, response: str, expected_count: int) -> List[str]:
        """Parse multiple image prompts from LLM response"""
        prompts = []
        
        for line in response.split('\n'):
            line = line.strip()
            
            # Look for numbered prompts
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering
                prompt = line.split('.', 1)[-1].strip()
                prompt = prompt.lstrip('-').strip()
                
                if prompt and len(prompt) > 20:  # Reasonable prompt length
                    prompts.append(prompt)
        
        # Fill with generic prompts if needed
        while len(prompts) < expected_count:
            prompts.append(f"Abstract visualization of concept {len(prompts) + 1}")
        
        return prompts[:expected_count]
    
    async def _generate_single_image(self,
                                   prompt: str,
                                   item_id: str,
                                   image_index: int) -> GeneratedImage:
        """Generate single image with retries"""
        
        async with self.semaphore:
            for attempt in range(3):  # 3 retry attempts
                try:
                    await asyncio.sleep(attempt * 2)  # Exponential backoff
                    
                    # Get OpenAI provider
                    openai_config = self.config_manager.config.providers['openai']
                    api_key = self.config_manager.get_provider_api_key('openai')
                    
                    # Make request to OpenAI Images API
                    async with httpx.AsyncClient(timeout=60) as client:
                        response = await client.post(
                            "https://api.openai.com/v1/images/generations",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "prompt": prompt,
                                "n": 1,
                                "size": "1024x1024",
                                "response_format": "url"
                            }
                        )
                        
                        response.raise_for_status()
                        result = response.json()
                    
                    # Download the image
                    image_url = result['data'][0]['url']
                    filename = f"{item_id}_{image_index}_{uuid.uuid4().hex[:8]}.png"
                    file_path = self.images_dir / filename
                    
                    # Download and save image
                    async with httpx.AsyncClient() as client:
                        img_response = await client.get(image_url)
                        img_response.raise_for_status()
                        
                        with open(file_path, 'wb') as f:
                            f.write(img_response.content)
                    
                    # Verify file was created and has content
                    if file_path.exists() and file_path.stat().st_size > 1000:  # At least 1KB
                        return GeneratedImage(
                            prompt=prompt,
                            file_path=str(file_path),
                            url=image_url,
                            metadata={
                                'size': "1024x1024",
                                'format': "png",
                                'file_size': file_path.stat().st_size,
                                'generated_at': datetime.now().isoformat(),
                                'attempt': attempt + 1
                            }
                        )
                    else:
                        raise ValueError("Generated image file is invalid or too small")
                    
                except Exception as e:
                    self.logger.warning(f"Image generation attempt {attempt + 1} failed: {e}")
                    if attempt == 2:  # Last attempt
                        raise
                    continue