"""
Professional Lambda client for EC2 integration
Handles triggering Lambda indexing and monitoring progress
"""

import json
import time
import boto3
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class IndexingStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class IndexingJob:
    job_id: str
    status: IndexingStatus
    started_at: float
    completed_at: Optional[float] = None
    documents_processed: int = 0
    total_documents: int = 0
    error_message: Optional[str] = None
    cache_size_mb: float = 0.0

class LambdaIndexingClient:
    """Professional client for Lambda-based RAG indexing"""
    
    def __init__(self, 
                 function_name: str = "holowellness-rag-indexer",
                 region: str = "ap-northeast-3",
                 s3_bucket: str = "holowellness",
                 s3_cache_prefix: str = "cache/current/"):
        
        self.function_name = function_name
        self.region = region
        self.s3_bucket = s3_bucket
        self.s3_cache_prefix = s3_cache_prefix
        
        # Initialize AWS clients
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        
        # Job tracking
        self.current_job: Optional[IndexingJob] = None
        
    def trigger_indexing(self, 
                        wait_for_completion: bool = True,
                        timeout_seconds: int = 900) -> IndexingJob:
        """
        Trigger Lambda indexing job with professional error handling
        
        Args:
            wait_for_completion: Whether to wait for job completion
            timeout_seconds: Maximum time to wait for completion
            
        Returns:
            IndexingJob with status and results
        """
        
        job_id = f"idx_{int(time.time())}"
        logger.info(f"Triggering Lambda indexing job: {job_id}")
        
        try:
            # Prepare Lambda payload
            payload = {
                "job_id": job_id,
                "triggered_by": "ec2_app",
                "timestamp": time.time()
            }
            
            # Invoke Lambda function asynchronously
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='Event' if not wait_for_completion else 'RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Create job tracking object
            self.current_job = IndexingJob(
                job_id=job_id,
                status=IndexingStatus.IN_PROGRESS,
                started_at=time.time()
            )
            
            if wait_for_completion:
                return self._wait_for_completion(timeout_seconds)
            else:
                logger.info(f"Indexing job {job_id} triggered asynchronously")
                return self.current_job
                
        except Exception as e:
            error_msg = f"Failed to trigger indexing: {str(e)}"
            logger.error(error_msg)
            
            return IndexingJob(
                job_id=job_id,
                status=IndexingStatus.FAILED,
                started_at=time.time(),
                completed_at=time.time(),
                error_message=error_msg
            )
    
    def _wait_for_completion(self, timeout_seconds: int) -> IndexingJob:
        """Wait for Lambda function completion with progress monitoring"""
        
        start_time = time.time()
        check_interval = 10  # Check every 10 seconds
        
        logger.info(f"Waiting for indexing completion (timeout: {timeout_seconds}s)")
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if cache files have been updated in S3
                cache_status = self._check_cache_status()
                
                if cache_status['updated']:
                    # Cache was updated, indexing likely completed
                    self.current_job.status = IndexingStatus.COMPLETED
                    self.current_job.completed_at = time.time()
                    self.current_job.cache_size_mb = cache_status.get('total_size_mb', 0)
                    
                    logger.info(f"Indexing completed successfully in {self.current_job.completed_at - self.current_job.started_at:.1f}s")
                    return self.current_job
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"Error checking completion status: {str(e)}")
                time.sleep(check_interval)
        
        # Timeout reached
        self.current_job.status = IndexingStatus.TIMEOUT
        self.current_job.completed_at = time.time()
        self.current_job.error_message = f"Indexing timed out after {timeout_seconds} seconds"
        
        logger.error(f"Indexing job timed out after {timeout_seconds} seconds")
        return self.current_job
    
    def _check_cache_status(self) -> Dict[str, Any]:
        """Check if S3 cache has been recently updated"""
        
        try:
            # Check manifest file for latest update
            manifest_key = f"{self.s3_cache_prefix}manifest.json"
            
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=manifest_key
            )
            
            manifest = json.loads(response['Body'].read())
            
            # Check if manifest is recent (within last few minutes)
            import datetime
            created_at = datetime.datetime.fromisoformat(manifest['created_at'].replace('Z', '+00:00'))
            age_seconds = (datetime.datetime.now(datetime.timezone.utc) - created_at).total_seconds()
            
            return {
                'updated': age_seconds < 300,  # Updated within last 5 minutes
                'total_size_mb': manifest.get('total_size_mb', 0),
                'documents_count': manifest.get('documents_count', 0),
                'created_at': manifest['created_at']
            }
            
        except Exception as e:
            logger.debug(f"Could not check cache status: {str(e)}")
            return {'updated': False}
    
    def get_indexing_status(self) -> Optional[IndexingJob]:
        """Get current indexing job status"""
        return self.current_job
    
    def download_fresh_cache(self) -> Tuple[bool, str]:
        """
        Download fresh cache from S3 after indexing completion
        
        Returns:
            Tuple of (success, message)
        """
        
        try:
            from s3_cache import S3CacheManager  # Import your existing S3 cache manager
            
            cache_manager = S3CacheManager(
                bucket=self.s3_bucket,
                prefix=self.s3_cache_prefix
            )
            
            # Download latest cache
            success = cache_manager.download_cache()
            
            if success:
                logger.info("Successfully downloaded fresh cache from S3")
                return True, "Cache downloaded successfully"
            else:
                return False, "Failed to download cache from S3"
                
        except Exception as e:
            error_msg = f"Error downloading cache: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def reindex_and_update(self, timeout_seconds: int = 900) -> Dict[str, Any]:
        """
        Complete reindexing workflow: trigger Lambda, wait, download cache
        
        Returns:
            Dict with operation results
        """
        
        logger.info("Starting complete reindexing workflow")
        
        # Step 1: Trigger indexing
        job = self.trigger_indexing(wait_for_completion=True, timeout_seconds=timeout_seconds)
        
        if job.status != IndexingStatus.COMPLETED:
            return {
                'success': False,
                'status': job.status.value,
                'error': job.error_message,
                'job_id': job.job_id
            }
        
        # Step 2: Download fresh cache
        cache_success, cache_message = self.download_fresh_cache()
        
        # Step 3: Return comprehensive results
        return {
            'success': cache_success,
            'status': 'completed' if cache_success else 'cache_download_failed',
            'job_id': job.job_id,
            'processing_time': job.completed_at - job.started_at,
            'documents_processed': job.documents_processed,
            'cache_size_mb': job.cache_size_mb,
            'cache_download_success': cache_success,
            'cache_message': cache_message
        }

# Integration with existing Flask app
def integrate_lambda_indexing():
    """
    Integration function for existing Flask app
    Replace existing reindex endpoint with Lambda-based version
    """
    
    lambda_client = LambdaIndexingClient()
    
    def lambda_reindex_endpoint():
        """New reindex endpoint using Lambda"""
        try:
            result = lambda_client.reindex_and_update(timeout_seconds=600)  # 10 minutes
            
            if result['success']:
                return {
                    'status': 'success',
                    'message': 'Indexing completed successfully via Lambda',
                    'details': result
                }
            else:
                return {
                    'status': 'error',
                    'message': f"Indexing failed: {result.get('error', 'Unknown error')}",
                    'details': result
                }
                
        except Exception as e:
            logger.error(f"Lambda reindex failed: {str(e)}")
            return {
                'status': 'error',
                'message': f'Lambda indexing error: {str(e)}'
            }
    
    return lambda_reindex_endpoint