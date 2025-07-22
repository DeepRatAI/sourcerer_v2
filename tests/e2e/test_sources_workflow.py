import pytest
import asyncio
import httpx
import time
from typing import Dict, Any

class TestSourcesWorkflow:
    """End-to-end tests for the complete sources workflow"""
    
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
    
    def test_complete_sources_workflow(self, client):
        """Test complete sources management workflow"""
        
        # Step 1: List sources (should be empty initially)
        response = client.get("/api/sources/")
        assert response.status_code == 200
        sources_data = response.json()
        initial_count = len(sources_data["data"])
        
        # Step 2: Add a new RSS source
        new_source = {
            "name": "Test RSS Feed",
            "type": "rss",
            "url": "https://feeds.feedburner.com/TechCrunch",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=new_source)
        assert response.status_code == 200
        created_source = response.json()["data"]
        source_id = created_source["id"]
        
        assert created_source["name"] == new_source["name"]
        assert created_source["type"] == new_source["type"]
        assert created_source["url"] == new_source["url"]
        assert created_source["status"] == "active"
        
        # Step 3: Verify source appears in list
        response = client.get("/api/sources/")
        assert response.status_code == 200
        sources_data = response.json()
        assert len(sources_data["data"]) == initial_count + 1
        
        # Find our source in the list
        our_source = next(s for s in sources_data["data"] if s["id"] == source_id)
        assert our_source["name"] == new_source["name"]
        
        # Step 4: Get specific source details
        response = client.get(f"/api/sources/{source_id}")
        assert response.status_code == 200
        source_details = response.json()["data"]
        assert source_details["id"] == source_id
        assert source_details["name"] == new_source["name"]
        
        # Step 5: Refresh the source manually
        response = client.post(f"/api/sources/{source_id}/refresh")
        assert response.status_code == 200
        
        # Step 6: Pause the source
        response = client.post(f"/api/sources/{source_id}/pause")
        assert response.status_code == 200
        
        # Verify status changed
        response = client.get(f"/api/sources/{source_id}")
        assert response.status_code == 200
        source_details = response.json()["data"]
        assert source_details["status"] == "paused"
        
        # Step 7: Activate the source again
        response = client.post(f"/api/sources/{source_id}/activate")
        assert response.status_code == 200
        
        # Verify status changed back
        response = client.get(f"/api/sources/{source_id}")
        assert response.status_code == 200
        source_details = response.json()["data"]
        assert source_details["status"] == "active"
        
        # Step 8: Update source configuration
        updated_config = {
            "name": "Updated RSS Feed",
            "refresh_interval": 7200
        }
        
        response = client.put(f"/api/sources/{source_id}", json=updated_config)
        assert response.status_code == 200
        updated_source = response.json()["data"]
        assert updated_source["name"] == updated_config["name"]
        assert updated_source["refresh_interval"] == updated_config["refresh_interval"]
        
        # Step 9: Get source statistics
        response = client.get(f"/api/sources/{source_id}/stats")
        assert response.status_code == 200
        stats = response.json()["data"]
        assert "item_count" in stats
        assert "last_sync" in stats
        assert "sync_history" in stats
        
        # Step 10: Test HTML source creation
        html_source = {
            "name": "Test HTML Page",
            "type": "html",
            "url": "https://example.com",
            "refresh_interval": 1800
        }
        
        response = client.post("/api/sources/", json=html_source)
        assert response.status_code == 200
        html_created = response.json()["data"]
        html_source_id = html_created["id"]
        
        assert html_created["type"] == "html"
        
        # Step 11: Delete the HTML source
        response = client.delete(f"/api/sources/{html_source_id}")
        assert response.status_code == 200
        
        # Verify it's gone
        response = client.get(f"/api/sources/{html_source_id}")
        assert response.status_code == 404
        
        # Step 12: Delete the RSS source
        response = client.delete(f"/api/sources/{source_id}")
        assert response.status_code == 200
        
        # Verify sources list is back to original count
        response = client.get("/api/sources/")
        assert response.status_code == 200
        sources_data = response.json()
        assert len(sources_data["data"]) == initial_count
        
    def test_source_validation(self, client):
        """Test source validation and error handling"""
        
        # Test missing required fields
        invalid_source = {
            "name": "Test Source"
            # Missing type and url
        }
        
        response = client.post("/api/sources/", json=invalid_source)
        assert response.status_code == 422  # Validation error
        
        # Test invalid URL
        invalid_url_source = {
            "name": "Invalid URL Source",
            "type": "rss",
            "url": "not-a-valid-url",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=invalid_url_source)
        assert response.status_code == 400  # Bad request
        
        # Test invalid source type
        invalid_type_source = {
            "name": "Invalid Type Source",
            "type": "invalid_type",
            "url": "https://example.com",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=invalid_type_source)
        assert response.status_code == 422  # Validation error
        
        # Test invalid refresh interval
        invalid_interval_source = {
            "name": "Invalid Interval Source",
            "type": "rss",
            "url": "https://example.com",
            "refresh_interval": 100  # Too small
        }
        
        response = client.post("/api/sources/", json=invalid_interval_source)
        assert response.status_code == 422  # Validation error
        
    def test_source_ingestion_simulation(self, client):
        """Test source ingestion with mock data"""
        
        # Create a test source
        test_source = {
            "name": "Ingestion Test Feed",
            "type": "rss",
            "url": "https://feeds.feedburner.com/oreilly/radar",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=test_source)
        assert response.status_code == 200
        source = response.json()["data"]
        source_id = source["id"]
        
        try:
            # Trigger manual refresh and wait for ingestion
            response = client.post(f"/api/sources/{source_id}/refresh")
            assert response.status_code == 200
            
            # Wait a bit for ingestion to process
            time.sleep(2)
            
            # Check if any items were ingested
            response = client.get(f"/api/sources/{source_id}/items")
            assert response.status_code == 200
            items_data = response.json()["data"]
            
            # We might not get items due to network issues, but the endpoint should work
            assert "items" in items_data
            assert "count" in items_data
            
            # Check source statistics
            response = client.get(f"/api/sources/{source_id}/stats")
            assert response.status_code == 200
            stats = response.json()["data"]
            assert "last_sync" in stats
            assert "sync_history" in stats
            
        finally:
            # Cleanup
            client.delete(f"/api/sources/{source_id}")
    
    def test_bulk_operations(self, client):
        """Test bulk source operations"""
        
        # Create multiple sources
        sources_data = []
        source_ids = []
        
        for i in range(3):
            source = {
                "name": f"Bulk Test Source {i+1}",
                "type": "rss",
                "url": f"https://example{i+1}.com/feed",
                "refresh_interval": 3600
            }
            
            response = client.post("/api/sources/", json=source)
            assert response.status_code == 200
            created_source = response.json()["data"]
            source_ids.append(created_source["id"])
            sources_data.append(created_source)
        
        try:
            # Test bulk pause operation
            bulk_pause_request = {"source_ids": source_ids}
            response = client.post("/api/sources/bulk/pause", json=bulk_pause_request)
            assert response.status_code == 200
            
            # Verify all sources are paused
            for source_id in source_ids:
                response = client.get(f"/api/sources/{source_id}")
                assert response.status_code == 200
                source = response.json()["data"]
                assert source["status"] == "paused"
            
            # Test bulk activate operation
            bulk_activate_request = {"source_ids": source_ids[:2]}  # Only first 2
            response = client.post("/api/sources/bulk/activate", json=bulk_activate_request)
            assert response.status_code == 200
            
            # Verify first 2 are active, last one still paused
            for i, source_id in enumerate(source_ids):
                response = client.get(f"/api/sources/{source_id}")
                assert response.status_code == 200
                source = response.json()["data"]
                expected_status = "active" if i < 2 else "paused"
                assert source["status"] == expected_status
            
            # Test bulk refresh operation
            bulk_refresh_request = {"source_ids": source_ids}
            response = client.post("/api/sources/bulk/refresh", json=bulk_refresh_request)
            assert response.status_code == 200
            
        finally:
            # Cleanup - delete all test sources
            for source_id in source_ids:
                client.delete(f"/api/sources/{source_id}")
    
    def test_scheduler_integration(self, client):
        """Test scheduler integration with sources"""
        
        # Get scheduler status
        response = client.get("/api/sources/scheduler/status")
        assert response.status_code == 200
        scheduler_status = response.json()["data"]
        assert "running" in scheduler_status
        assert "job_count" in scheduler_status
        
        # Create a source with short refresh interval for testing
        test_source = {
            "name": "Scheduler Test Source",
            "type": "rss", 
            "url": "https://example.com/feed",
            "refresh_interval": 60  # 1 minute for testing
        }
        
        response = client.post("/api/sources/", json=test_source)
        assert response.status_code == 200
        source = response.json()["data"]
        source_id = source["id"]
        
        try:
            # Check scheduler status again - should have one more job
            response = client.get("/api/sources/scheduler/status")
            assert response.status_code == 200
            new_scheduler_status = response.json()["data"]
            
            # Job count might increase (depending on existing jobs)
            assert new_scheduler_status["running"] == scheduler_status["running"]
            
            # Get scheduled jobs
            response = client.get("/api/sources/scheduler/jobs")
            assert response.status_code == 200
            jobs_data = response.json()["data"]
            assert "jobs" in jobs_data
            
            # Look for our source's job
            job_found = False
            for job in jobs_data["jobs"]:
                if source_id in str(job):
                    job_found = True
                    break
            
            # The job should be scheduled
            assert job_found or len(jobs_data["jobs"]) > 0
            
        finally:
            # Cleanup
            client.delete(f"/api/sources/{source_id}")
            
    def test_error_recovery(self, client):
        """Test error handling and recovery scenarios"""
        
        # Create a source with an invalid URL that will cause sync errors
        error_source = {
            "name": "Error Test Source",
            "type": "rss",
            "url": "https://nonexistent-domain-12345.com/feed",
            "refresh_interval": 3600
        }
        
        response = client.post("/api/sources/", json=error_source)
        assert response.status_code == 200
        source = response.json()["data"]
        source_id = source["id"]
        
        try:
            # Trigger refresh which should fail
            response = client.post(f"/api/sources/{source_id}/refresh")
            # The refresh endpoint should accept the request even if sync fails
            assert response.status_code == 200
            
            # Wait a moment for the sync attempt
            time.sleep(1)
            
            # Check source status - it might be in error state
            response = client.get(f"/api/sources/{source_id}")
            assert response.status_code == 200
            source_details = response.json()["data"]
            
            # The source should still exist and be manageable
            assert source_details["id"] == source_id
            
            # Check error logs/history if available
            response = client.get(f"/api/sources/{source_id}/stats")
            assert response.status_code == 200
            stats = response.json()["data"]
            
            # Should have sync history even with errors
            assert "sync_history" in stats
            
        finally:
            # Cleanup
            client.delete(f"/api/sources/{source_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])