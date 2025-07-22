from fastapi import APIRouter, HTTPException, Depends
from typing import List

from ..models.api import APIResponse
from ..models.content import GenerateContentRequest, ContentPackage
from ..generation.pipeline import ContentGenerationPipeline
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("sourcerer.api.content")


def get_generation_pipeline() -> ContentGenerationPipeline:
    """Get content generation pipeline dependency"""
    return ContentGenerationPipeline()


@router.post("/generate")
async def generate_content(
    request: GenerateContentRequest,
    pipeline: ContentGenerationPipeline = Depends(get_generation_pipeline)
):
    """Generate content package from source item"""
    try:
        logger.info(f"Starting content generation for item: {request.source_item_id}")
        
        # Validate request
        if not request.content_types:
            raise ValueError("At least one content type must be specified")
        
        if not request.source_item_id:
            raise ValueError("Source item ID is required")
        
        # Generate content package
        content_package = await pipeline.generate_content_package(request)
        
        return APIResponse(data={
            "package": content_package.model_dump(),
            "message": "Content package generated successfully"
        })
        
    except ValueError as e:
        logger.error(f"Content generation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {e}")


@router.get("/packages")
async def list_content_packages(
    pipeline: ContentGenerationPipeline = Depends(get_generation_pipeline)
):
    """List generated content packages"""
    try:
        packages = pipeline.list_content_packages()
        return APIResponse(data={
            "packages": packages,
            "count": len(packages)
        })
    except Exception as e:
        logger.error(f"Failed to list content packages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list content packages: {e}")


@router.get("/packages/{package_id}")
async def get_content_package(
    package_id: str,
    pipeline: ContentGenerationPipeline = Depends(get_generation_pipeline)
):
    """Get content package details"""
    try:
        package = pipeline.get_content_package(package_id)
        
        if not package:
            raise HTTPException(status_code=404, detail="Content package not found")
        
        return APIResponse(data=package.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content package: {e}")


@router.delete("/packages/{package_id}")
async def delete_content_package(
    package_id: str,
    pipeline: ContentGenerationPipeline = Depends(get_generation_pipeline)
):
    """Delete content package"""
    try:
        success = pipeline.delete_content_package(package_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Content package not found")
        
        return APIResponse(data={"message": f"Content package {package_id} deleted successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete content package: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete content package: {e}")


@router.get("/stats")
async def get_content_stats(
    pipeline: ContentGenerationPipeline = Depends(get_generation_pipeline)
):
    """Get content generation statistics"""
    try:
        packages = pipeline.list_content_packages()
        
        # Calculate stats
        total_packages = len(packages)
        packages_with_research = sum(1 for p in packages if p.get('has_research', False))
        total_files = sum(p.get('file_count', 0) for p in packages)
        
        # Content type breakdown
        content_type_counts = {}
        for package in packages:
            # This would need to be calculated from actual package data
            # For now, return basic stats
            pass
        
        stats = {
            'total_packages': total_packages,
            'packages_with_research': packages_with_research,
            'total_generated_files': total_files,
            'content_type_breakdown': content_type_counts
        }
        
        return APIResponse(data=stats)
        
    except Exception as e:
        logger.error(f"Failed to get content stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content stats: {e}")


@router.post("/test-generation")
async def test_content_generation(
    source_item_id: str,
    pipeline: ContentGenerationPipeline = Depends(get_generation_pipeline)
):
    """Test content generation with minimal configuration"""
    try:
        from ..models.content import ContentType
        
        # Create minimal test request
        test_request = GenerateContentRequest(
            source_item_id=source_item_id,
            content_types=[ContentType.SUMMARY],
            include_research=False,
            platforms=[],
            image_count=0
        )
        
        # Generate test content
        content_package = await pipeline.generate_content_package(test_request)
        
        return APIResponse(data={
            "test_successful": True,
            "package_id": content_package.id,
            "content_count": len(content_package.contents),
            "message": "Test content generation completed successfully"
        })
        
    except Exception as e:
        logger.error(f"Test content generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test content generation failed: {e}")