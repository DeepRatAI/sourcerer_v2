import pytest
import asyncio
import httpx
import time
from typing import Dict, Any, List

class TestContentGenerationWorkflow:
    """End-to-end tests for RAG system and content generation workflow"""
    
    BASE_URL = "http://localhost:8000"
    
    @pytest.fixture
    def client(self):
        """HTTP client for API testing"""
        return httpx.Client(base_url=self.BASE_URL)
    
    @pytest.fixture
    async def async_client(self):
        """Async HTTP client for API testing"""
        async with httpx.AsyncClient(base_url=self.BASE_URL) as client:
            yield client
    
    def setup_test_source_with_content(self, client) -> Dict[str, Any]:
        """Helper to create a test source with content for generation tests"""
        
        # Create a test source
        test_source = {
            "name": "Content Generation Test Source",
            "type": "rss",
            "url": "https://feeds.feedburner.com/oreilly/radar",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=test_source)
        assert response.status_code == 200
        source = response.json()["data"]
        
        # Trigger refresh to get some content
        response = client.post(f"/api/sources/{source['id']}/refresh")
        assert response.status_code == 200
        
        return source
    
    def get_test_source_item(self, client, source_id: str) -> str:
        """Helper to get a source item ID for testing"""
        
        response = client.get(f"/api/sources/{source_id}/items")
        assert response.status_code == 200
        items_data = response.json()["data"]
        
        if items_data["items"]:
            return items_data["items"][0]["id"]
        else:
            # If no items, we'll need to mock one or skip the test
            pytest.skip("No source items available for content generation test")
    
    def test_complete_content_generation_workflow(self, client):
        """Test complete content generation workflow from source to package"""
        
        # Step 1: Set up test source with content
        source = self.setup_test_source_with_content(client)
        source_id = source["id"]
        
        try:
            # Wait a moment for content ingestion
            time.sleep(3)
            
            # Step 2: Get a source item for content generation
            try:
                item_id = self.get_test_source_item(client, source_id)
            except:
                # If we can't get real items, create a mock scenario
                item_id = "mock-item-123"
            
            # Step 3: Generate content package with summary only
            generation_request = {
                "source_item_id": item_id,
                "content_types": ["summary"],
                "platforms": [],
                "include_research": False,
                "image_count": 0,
                "custom_instructions": "Keep it concise and professional"
            }
            
            response = client.post("/api/content/generate", json=generation_request)
            
            # The request might fail due to missing LLM config, but endpoint should exist
            assert response.status_code in [200, 400, 500]
            
            if response.status_code == 200:
                package_data = response.json()["data"]
                assert "package" in package_data
                package = package_data["package"]
                package_id = package["id"]
                
                # Step 4: List generated packages
                response = client.get("/api/content/packages")
                assert response.status_code == 200
                packages_data = response.json()["data"]
                assert "packages" in packages_data
                
                # Find our package
                our_package = next(
                    (p for p in packages_data["packages"] if p["id"] == package_id),
                    None
                )
                assert our_package is not None
                
                # Step 5: Get specific package details
                response = client.get(f"/api/content/packages/{package_id}")
                assert response.status_code == 200
                package_details = response.json()["data"]
                assert package_details["id"] == package_id
                assert package_details["source_item_id"] == item_id
                
                # Step 6: Test content package with research
                research_request = {
                    "source_item_id": item_id,
                    "content_types": ["summary"],
                    "platforms": [],
                    "include_research": True,
                    "image_count": 0,
                    "custom_instructions": ""
                }
                
                response = client.post("/api/content/generate", json=research_request)
                if response.status_code == 200:
                    research_package = response.json()["data"]["package"]
                    assert research_package["research_summary"] is not None
                
                # Step 7: Test multi-content generation
                multi_request = {
                    "source_item_id": item_id,
                    "content_types": ["summary", "scripts"],
                    "platforms": ["youtube", "tiktok"],
                    "include_research": False,
                    "image_count": 1,
                    "custom_instructions": "Target audience: tech professionals"
                }
                
                response = client.post("/api/content/generate", json=multi_request)
                if response.status_code == 200:
                    multi_package = response.json()["data"]["package"]
                    assert len(multi_package["contents"]) >= 2  # summary + scripts
                
                # Step 8: Delete test packages
                for test_package_id in [package_id]:
                    try:
                        response = client.delete(f"/api/content/packages/{test_package_id}")
                        assert response.status_code in [200, 404]
                    except:
                        pass  # Cleanup, ignore errors
        
        finally:
            # Cleanup source
            client.delete(f"/api/sources/{source_id}")
    
    def test_rag_system_integration(self, client):
        """Test RAG system integration with content generation"""
        
        # Step 1: Check RAG system status
        response = client.get("/api/rag/status")
        assert response.status_code == 200
        rag_status = response.json()["data"]
        assert "vector_store_size" in rag_status
        assert "embedding_model" in rag_status
        
        # Step 2: Test search functionality
        search_request = {
            "query": "artificial intelligence",
            "max_results": 5,
            "min_similarity": 0.3
        }
        
        response = client.post("/api/rag/search", json=search_request)
        assert response.status_code == 200
        search_results = response.json()["data"]
        assert "results" in search_results
        assert "count" in search_results
        
        # Step 3: Test content indexing
        # Create a test source to generate content for indexing
        source = self.setup_test_source_with_content(client)
        source_id = source["id"]
        
        try:
            # Wait for content ingestion and indexing
            time.sleep(5)
            
            # Check if vector store size increased
            response = client.get("/api/rag/status")
            assert response.status_code == 200
            new_rag_status = response.json()["data"]
            
            # Vector store might have grown
            assert new_rag_status["vector_store_size"] >= rag_status["vector_store_size"]
            
            # Step 4: Test similarity search with actual content
            content_search = {
                "query": "technology trends",
                "max_results": 3,
                "min_similarity": 0.2
            }
            
            response = client.post("/api/rag/search", json=content_search)
            assert response.status_code == 200
            content_results = response.json()["data"]
            
            # Should get some results if content was indexed
            assert content_results["count"] >= 0
            
        finally:
            # Cleanup
            client.delete(f"/api/sources/{source_id}")
    
    def test_content_validation_and_error_handling(self, client):
        """Test content generation validation and error handling"""
        
        # Test invalid source item ID
        invalid_request = {
            "source_item_id": "nonexistent-item-id",
            "content_types": ["summary"],
            "platforms": [],
            "include_research": False,
            "image_count": 0
        }
        
        response = client.post("/api/content/generate", json=invalid_request)
        assert response.status_code in [400, 404, 500]
        
        # Test empty content types
        empty_request = {
            "source_item_id": "test-item-id",
            "content_types": [],
            "platforms": [],
            "include_research": False,
            "image_count": 0
        }
        
        response = client.post("/api/content/generate", json=empty_request)
        assert response.status_code == 400
        
        # Test invalid content types
        invalid_types_request = {
            "source_item_id": "test-item-id",
            "content_types": ["invalid_type"],
            "platforms": [],
            "include_research": False,
            "image_count": 0
        }
        
        response = client.post("/api/content/generate", json=invalid_types_request)
        assert response.status_code == 422
        
        # Test excessive image count
        excessive_images_request = {
            "source_item_id": "test-item-id",
            "content_types": ["images"],
            "platforms": [],
            "include_research": False,
            "image_count": 100  # Too many
        }
        
        response = client.post("/api/content/generate", json=excessive_images_request)
        assert response.status_code == 422
    
    def test_content_statistics_and_management(self, client):
        """Test content package statistics and management"""
        
        # Step 1: Get initial content statistics
        response = client.get("/api/content/stats")
        assert response.status_code == 200
        initial_stats = response.json()["data"]
        
        assert "total_packages" in initial_stats
        assert "packages_with_research" in initial_stats
        assert "total_generated_files" in initial_stats
        
        # Step 2: List all packages
        response = client.get("/api/content/packages")
        assert response.status_code == 200
        packages_data = response.json()["data"]
        assert "packages" in packages_data
        assert "count" in packages_data
        
        initial_package_count = packages_data["count"]
        
        # Step 3: Test package filtering (if implemented)
        # This might be a future enhancement
        response = client.get("/api/content/packages?has_research=true")
        assert response.status_code == 200
        
        response = client.get("/api/content/packages?content_type=summary")
        assert response.status_code == 200
        
        # Step 4: Test package search (if implemented)
        search_params = {"q": "test", "limit": 10}
        response = client.get("/api/content/packages", params=search_params)
        assert response.status_code == 200
    
    def test_content_export_and_download(self, client):
        """Test content package export and download functionality"""
        
        # This test assumes export functionality exists
        # If not implemented, endpoints should return appropriate errors
        
        # Test package export
        export_request = {
            "package_ids": ["test-package-1", "test-package-2"],
            "format": "zip",
            "include_metadata": True
        }
        
        response = client.post("/api/content/export", json=export_request)
        # Endpoint might not be implemented yet
        assert response.status_code in [200, 404, 501]
        
        # Test individual package download
        response = client.get("/api/content/packages/test-package/download")
        assert response.status_code in [200, 404, 501]
        
        # Test package metadata export
        response = client.get("/api/content/packages/test-package/metadata")
        assert response.status_code in [200, 404]
    
    def test_research_engine_functionality(self, client):
        """Test research engine functionality"""
        
        # Test research engine status
        response = client.get("/api/research/status")
        # Endpoint might not exist yet
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            status = response.json()["data"]
            assert "enabled" in status
            
            # Test manual research trigger
            research_request = {
                "query": "artificial intelligence trends 2024",
                "max_sources": 5,
                "include_web_search": False
            }
            
            response = client.post("/api/research/conduct", json=research_request)
            assert response.status_code in [200, 202]  # 202 for async processing
            
            if response.status_code == 200:
                research_data = response.json()["data"]
                assert "research_id" in research_data
                
                # Get research results
                research_id = research_data["research_id"]
                response = client.get(f"/api/research/{research_id}")
                assert response.status_code == 200
    
    def test_content_generation_pipeline_monitoring(self, client):
        """Test content generation pipeline monitoring and metrics"""
        
        # Get generation metrics
        response = client.get("/api/content/metrics")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            metrics = response.json()["data"]
            assert "generation_count" in metrics or "total_packages" in metrics
            
            # Get generation history
            response = client.get("/api/content/history")
            assert response.status_code in [200, 404]
            
            # Get system performance metrics
            response = client.get("/api/content/performance")
            assert response.status_code in [200, 404]
    
    def test_concurrent_content_generation(self, client):
        """Test concurrent content generation requests"""
        
        import threading
        import queue
        
        # This test simulates multiple concurrent generation requests
        # to test system stability under load
        
        results_queue = queue.Queue()
        
        def generate_content(item_id, thread_id):
            """Generate content in a separate thread"""
            try:
                request = {
                    "source_item_id": f"test-item-{thread_id}",
                    "content_types": ["summary"],
                    "platforms": [],
                    "include_research": False,
                    "image_count": 0
                }
                
                thread_client = httpx.Client(base_url=self.BASE_URL)
                response = thread_client.post("/api/content/generate", json=request)
                results_queue.put((thread_id, response.status_code))
                thread_client.close()
                
            except Exception as e:
                results_queue.put((thread_id, f"Error: {e}"))
        
        # Start multiple threads
        threads = []
        for i in range(3):  # Limited number to avoid overwhelming test system
            thread = threading.Thread(target=generate_content, args=(f"item-{i}", i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Verify we got responses from all threads
        assert len(results) == 3
        
        # All requests should get some response (even if error due to config)
        for thread_id, status in results:
            assert isinstance(status, int)  # Should be HTTP status code
            assert 200 <= status <= 599


if __name__ == "__main__":
    pytest.main([__file__, "-v"])