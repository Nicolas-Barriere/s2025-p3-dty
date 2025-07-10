import os
import json
import requests
import logging
import wget
import uuid

from .config import AlbertConfig
from .api_client import AlbertAPIClient

logger = logging.getLogger(__name__)

class RAGSystem:
    """System for Retrieval-Augmented Generation with Albert API."""

    def __init__(self):
        """Initialize the RAG system."""
        self.config = AlbertConfig()
        self.api_client = AlbertAPIClient(self.config)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.config.api_key}',
        })
        self.collection_name = f"email-collection-{uuid.uuid4()}"
        self.collection_id = None
        self.embeddings_model = None

    def _get_models(self):
        """Get available models from the API using direct HTTP requests."""
        if self.embeddings_model:
            return
        
        # Use direct HTTP requests instead of OpenAI client to avoid compatibility issues
        # Following the Albert API documentation pattern
        try:
            response = self.session.get(f"{self.config.base_url}/models")
            response.raise_for_status()
            models_data = response.json()
            
            # Look for embedding model
            for model in models_data.get('data', []):
                if model.get('type') == "text-embeddings-inference":
                    self.embeddings_model = model.get('id')
                    break
                    
            if not self.embeddings_model:
                # Fallback to a default embedding model if none found
                self.embeddings_model = "embeddings-small"
                
        except Exception as e:
            logger.error(f"Failed to get models from Albert API: {e}")
            # Use default embedding model as fallback
            self.embeddings_model = "embeddings-small"

    def create_collection(self):
        """Create a new collection for emails."""
        self._get_models()
        if not self.embeddings_model:
            raise Exception("No embedding model found.")

        response = self.session.post(
            f"{self.config.base_url}/collections",
            json={"name": self.collection_name, "model": self.embeddings_model}
        )
        response.raise_for_status()
        self.collection_id = response.json()["id"]
        print(f"Collection '{self.collection_name}' created with ID: {self.collection_id}")

    def index_emails(self, emails: list[dict]):
        """
        Index a list of emails.

        Args:
            emails: A list of dictionaries, where each dictionary represents an email
                    with at least a 'body' key.
        """
        if not self.collection_id:
            self.create_collection()

        successful_indexes = 0
        failed_indexes = 0

        for i, email in enumerate(emails):
            try:
                # Limit email body size to avoid API issues
                email_body = email.get('body', '')
                if len(email_body) > self.config.max_email_content_length:
                    email_body = email_body[:self.config.max_email_content_length] + "... [truncated]"
                
                # Clean the email body to remove potential problematic characters
                email_body = email_body.encode('utf-8', errors='ignore').decode('utf-8')
                
                # Create a temporary file with the email body
                file_path = f"/tmp/email_{i}_{email.get('id', 'unknown')}.txt"
                with open(file_path, "w", encoding='utf-8') as f:
                    f.write(email_body)

                # Prepare metadata with email ID for better matching
                metadata = email.get('metadata', {})
                metadata['email_id'] = email.get('id', 'unknown')
                metadata['document_name'] = os.path.basename(file_path)

                with open(file_path, "rb") as f:
                    files = {'file': (os.path.basename(file_path), f, 'text/plain')}
                    # Include metadata in the request
                    request_data = {
                        "collection": self.collection_id,
                        "metadata": metadata
                    }
                    data = {'request': json.dumps(request_data)}
                    
                    response = self.session.post(
                        f"{self.config.base_url}/files",
                        data=data,
                        files=files,
                        timeout=30  # Add timeout
                    )
                    
                    if response.status_code != 201:
                        logger.warning(f"Failed to index email {i+1}: Status {response.status_code}")
                        logger.warning(f"Response: {response.text}")
                        failed_indexes += 1
                    else:
                        successful_indexes += 1
                        logger.debug(f"Successfully indexed email {i+1}/{len(emails)}")
                
                os.remove(file_path)
                
                # Add a small delay to avoid overwhelming the API
                if i > 0 and i % 10 == 0:
                    import time
                    time.sleep(self.config.batch_upload_delay)  # Configurable delay
                    
            except Exception as e:
                failed_indexes += 1
                logger.error(f"Error indexing email {i+1}: {e}")
                # Clean up the temp file if it exists
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
                continue

        logger.info(f"Email indexing completed: {successful_indexes} successful, {failed_indexes} failed")
        
        if successful_indexes == 0:
            raise Exception(f"Failed to index any emails. All {failed_indexes} attempts failed.")
        elif failed_indexes > 0:
            logger.warning(f"Some emails failed to index: {failed_indexes} out of {len(emails)}")
        
        print(f"Successfully indexed {successful_indexes}/{len(emails)} emails")

    def query_emails(self, query: str, k: int = 5) -> list[dict]:
        """
        Query the indexed emails to find the most relevant ones.

        Args:
            query: The user's query.
            k: The number of emails to retrieve.

        Returns:
            A list of dictionaries containing content and metadata for matching.
        """
        if not self.collection_id:
            raise Exception("Collection does not exist. Please index emails first.")

        data = {
            "collections": [self.collection_id],
            "k": k,
            "prompt": query,
            "method": "semantic"
        }
        response = self.session.post(
            url=f"{self.config.base_url}/search",
            json=data
        )
        response.raise_for_status()
        
        results = response.json()["data"]
        
        # Return both content and metadata for better matching
        formatted_results = []
        for result in results:
            chunk = result["chunk"]
            formatted_results.append({
                "content": chunk["content"],
                "metadata": chunk.get("metadata", {}),
                "score": result.get("score", 0.0),
                "document_name": chunk.get("metadata", {}).get("document_name", "")
            })
        
        return formatted_results

