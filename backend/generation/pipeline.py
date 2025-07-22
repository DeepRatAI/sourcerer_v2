import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..models.source import SourceItem
from ..models.content import (
    GenerateContentRequest, ContentPackage, ContentType, 
    GeneratedContent, ResearchDocument
)
from ..config.paths import get_outputs_dir
from ..utils.file_utils import safe_write_json, ensure_directory
from ..utils.logging import get_logger
from .research import ResearchEngine
from .generators import SummaryGenerator, ScriptGenerator, ImageGenerator


class ContentGenerationPipeline:
    """Main pipeline for orchestrating content generation"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.generation.pipeline")
        self.outputs_dir = get_outputs_dir()
        self.packages_dir = self.outputs_dir / "packages"
        ensure_directory(self.packages_dir)
        
        # Initialize engines
        self.research_engine = ResearchEngine()
        self.summary_generator = SummaryGenerator()
        self.script_generator = ScriptGenerator()
        self.image_generator = ImageGenerator()
    
    async def generate_content_package(self, request: GenerateContentRequest) -> ContentPackage:
        """Generate complete content package for a source item"""
        
        try:
            self.logger.info(f"Starting content generation for item: {request.source_item_id}")
            
            # Get source item
            source_item = await self._get_source_item(request.source_item_id)
            if not source_item:
                raise ValueError(f"Source item {request.source_item_id} not found")
            
            # Create package ID
            package_id = str(uuid.uuid4())[:12]
            
            # Phase 1: Research (if enabled)
            research_doc = None
            if request.include_research:
                research_doc = await self._conduct_research_phase(source_item)
            
            # Phase 2: Content generation
            generated_contents = await self._generate_content_phase(
                source_item=source_item,
                request=request,
                research=research_doc
            )
            
            # Phase 3: Create and save package
            content_package = await self._create_content_package(
                package_id=package_id,
                source_item=source_item,
                request=request,
                research=research_doc,
                contents=generated_contents
            )
            
            self.logger.info(f"Content package {package_id} generated successfully")
            return content_package
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise
    
    async def _get_source_item(self, item_id: str) -> Optional[SourceItem]:
        """Get source item by ID"""
        try:
            from ..sources.manager import SourceManager
            
            source_manager = SourceManager()
            sources = source_manager.list_sources()
            
            # Search through all sources
            for source in sources:
                for item in source.items:
                    if item.id == item_id:
                        return item
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get source item: {e}")
            return None
    
    async def _conduct_research_phase(self, source_item: SourceItem) -> Optional[ResearchDocument]:
        """Conduct research phase"""
        try:
            self.logger.info("Starting research phase")
            research_doc = await self.research_engine.conduct_research(source_item)
            self.logger.info("Research phase completed")
            return research_doc
        except Exception as e:
            self.logger.error(f"Research phase failed: {e}")
            return None
    
    async def _generate_content_phase(self,
                                    source_item: SourceItem,
                                    request: GenerateContentRequest,
                                    research: Optional[ResearchDocument] = None) -> List[GeneratedContent]:
        """Generate all requested content types"""
        
        self.logger.info("Starting content generation phase")
        
        # Prepare generation tasks
        tasks = []
        
        # Summary generation
        if ContentType.SUMMARY in request.content_types:
            tasks.append(self._generate_summary(source_item, research, request.custom_instructions))
        
        # Scripts generation
        if ContentType.SCRIPTS in request.content_types:
            tasks.append(self._generate_scripts(
                source_item, 
                request.platforms, 
                research, 
                request.custom_instructions
            ))
        
        # Image generation  
        if ContentType.IMAGES in request.content_types:
            tasks.append(self._generate_images(
                source_item,
                request.image_count,
                research,
                request.custom_instructions
            ))
        
        # Execute all generation tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        generated_contents = []
        for result in results:
            if isinstance(result, GeneratedContent):
                generated_contents.append(result)
            else:
                self.logger.error(f"Content generation failed: {result}")
        
        self.logger.info(f"Generated {len(generated_contents)} content pieces")
        return generated_contents
    
    async def _generate_summary(self,
                              source_item: SourceItem,
                              research: Optional[ResearchDocument],
                              custom_instructions: Optional[str]) -> GeneratedContent:
        """Generate summary content"""
        try:
            return await self.summary_generator.generate_summary(
                item=source_item,
                research=research,
                custom_instructions=custom_instructions
            )
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            # Return error content
            return GeneratedContent(
                type=ContentType.SUMMARY,
                title=f"Summary Error: {source_item.title}",
                content=f"Summary generation failed: {str(e)}",
                metadata={'error': True}
            )
    
    async def _generate_scripts(self,
                              source_item: SourceItem,
                              platforms: List[str],
                              research: Optional[ResearchDocument],
                              custom_instructions: Optional[str]) -> GeneratedContent:
        """Generate scripts content"""
        try:
            return await self.script_generator.generate_scripts(
                item=source_item,
                platforms=platforms,
                research=research,
                custom_instructions=custom_instructions
            )
        except Exception as e:
            self.logger.error(f"Script generation failed: {e}")
            return GeneratedContent(
                type=ContentType.SCRIPTS,
                title=f"Scripts Error: {source_item.title}",
                scripts=[],
                metadata={'error': True, 'error_message': str(e)}
            )
    
    async def _generate_images(self,
                             source_item: SourceItem,
                             image_count: int,
                             research: Optional[ResearchDocument],
                             custom_instructions: Optional[str]) -> GeneratedContent:
        """Generate images content"""
        try:
            if image_count == 0:
                return GeneratedContent(
                    type=ContentType.IMAGES,
                    title=f"Images: {source_item.title}",
                    images=[],
                    metadata={'skipped': True}
                )
            
            return await self.image_generator.generate_images(
                item=source_item,
                image_count=image_count,
                research=research,
                custom_instructions=custom_instructions
            )
        except Exception as e:
            self.logger.error(f"Image generation failed: {e}")
            return GeneratedContent(
                type=ContentType.IMAGES,
                title=f"Images Error: {source_item.title}",
                images=[],
                metadata={'error': True, 'error_message': str(e)}
            )
    
    async def _create_content_package(self,
                                    package_id: str,
                                    source_item: SourceItem,
                                    request: GenerateContentRequest,
                                    research: Optional[ResearchDocument],
                                    contents: List[GeneratedContent]) -> ContentPackage:
        """Create and save content package"""
        
        # Collect all file paths
        file_paths = []
        for content in contents:
            if content.images:
                file_paths.extend([img.file_path for img in content.images])
        
        # Create content package
        package = ContentPackage(
            id=package_id,
            source_item_id=source_item.id,
            research_summary=research.summary if research else None,
            contents=contents,
            generation_params={
                'content_types': [ct.value for ct in request.content_types],
                'platforms': request.platforms,
                'image_count': request.image_count,
                'include_research': request.include_research,
                'custom_instructions': request.custom_instructions
            },
            file_paths=file_paths
        )
        
        # Save package to disk
        package_dir = self.packages_dir / package_id
        ensure_directory(package_dir)
        
        package_file = package_dir / "package.json"
        safe_write_json(package.model_dump(), package_file)
        
        self.logger.info(f"Saved content package: {package_id}")
        return package
    
    def list_content_packages(self) -> List[Dict[str, Any]]:
        """List all content packages"""
        packages = []
        
        try:
            if not self.packages_dir.exists():
                return packages
            
            for package_dir in self.packages_dir.iterdir():
                if package_dir.is_dir():
                    package_file = package_dir / "package.json"
                    
                    if package_file.exists():
                        try:
                            import json
                            with open(package_file, 'r') as f:
                                package_data = json.load(f)
                            
                            # Add summary info
                            package_summary = {
                                'id': package_data.get('id'),
                                'source_item_id': package_data.get('source_item_id'),
                                'created_at': package_data.get('created_at'),
                                'content_count': len(package_data.get('contents', [])),
                                'has_research': bool(package_data.get('research_summary')),
                                'file_count': len(package_data.get('file_paths', []))
                            }
                            packages.append(package_summary)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to read package {package_dir.name}: {e}")
            
            # Sort by creation date (newest first)
            packages.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list content packages: {e}")
        
        return packages
    
    def get_content_package(self, package_id: str) -> Optional[ContentPackage]:
        """Get specific content package"""
        try:
            package_file = self.packages_dir / package_id / "package.json"
            
            if package_file.exists():
                import json
                with open(package_file, 'r') as f:
                    package_data = json.load(f)
                
                return ContentPackage(**package_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get content package {package_id}: {e}")
            return None
    
    def delete_content_package(self, package_id: str) -> bool:
        """Delete content package and associated files"""
        try:
            package_dir = self.packages_dir / package_id
            
            if package_dir.exists():
                import shutil
                shutil.rmtree(package_dir)
                self.logger.info(f"Deleted content package: {package_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete content package {package_id}: {e}")
            return False