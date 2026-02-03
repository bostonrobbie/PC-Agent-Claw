#!/usr/bin/env python3
"""Data Pipeline (#43) - Automated data collection and processing"""
import sys
from pathlib import Path
from typing import Dict, List, Callable, Optional
from datetime import datetime
import json
import threading
import time

sys.path.append(str(Path(__file__).parent.parent))

from core.persistent_memory import PersistentMemory

class DataPipeline:
    """Pipeline for automated data collection and processing"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = str(workspace / "memory.db")

        self.memory = PersistentMemory(db_path)
        self.sources: Dict[str, Dict] = {}
        self.processors: List[Callable] = []
        self.running = False
        self.threads: List[threading.Thread] = []

    def register_source(self, name: str, fetch_func: Callable, interval_seconds: int = 60):
        """Register a data source"""
        self.sources[name] = {
            'fetch_func': fetch_func,
            'interval': interval_seconds,
            'last_fetch': None,
            'error_count': 0
        }

        self.memory.log_decision(
            f'Data source registered: {name}',
            f'Interval: {interval_seconds}s, Function: {fetch_func.__name__}',
            tags=['data_pipeline', 'source', name]
        )

    def register_processor(self, processor_func: Callable):
        """Register a data processor"""
        self.processors.append(processor_func)

        self.memory.log_decision(
            f'Data processor registered',
            f'Processor: {processor_func.__name__}',
            tags=['data_pipeline', 'processor']
        )

    def fetch_data(self, source_name: str) -> Optional[any]:
        """Fetch data from a specific source"""
        if source_name not in self.sources:
            return None

        source = self.sources[source_name]

        try:
            data = source['fetch_func']()
            source['last_fetch'] = datetime.now()
            source['error_count'] = 0

            self.memory.log_decision(
                f'Data fetched: {source_name}',
                f'Success, size: {len(str(data))} bytes',
                tags=['data_pipeline', 'fetch', source_name]
            )

            return data

        except Exception as e:
            source['error_count'] += 1

            self.memory.log_decision(
                f'Data fetch failed: {source_name}',
                f'Error: {str(e)}, Error count: {source["error_count"]}',
                tags=['data_pipeline', 'fetch_error', source_name]
            )

            return None

    def process_data(self, data: any, metadata: Dict = None) -> any:
        """Process data through all registered processors"""
        processed = data

        for processor in self.processors:
            try:
                processed = processor(processed, metadata or {})
            except Exception as e:
                self.memory.log_decision(
                    f'Data processing error',
                    f'Processor: {processor.__name__}, Error: {str(e)}',
                    tags=['data_pipeline', 'processing_error']
                )

        return processed

    def start(self):
        """Start the data pipeline"""
        if self.running:
            return

        self.running = True

        # Start a thread for each source
        for source_name, source in self.sources.items():
            thread = threading.Thread(
                target=self._source_worker,
                args=(source_name,),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)

        self.memory.log_decision(
            'Data pipeline started',
            f'Running {len(self.sources)} sources',
            tags=['data_pipeline', 'start']
        )

    def stop(self):
        """Stop the data pipeline"""
        self.running = False

        self.memory.log_decision(
            'Data pipeline stopped',
            f'Stopped {len(self.sources)} sources',
            tags=['data_pipeline', 'stop']
        )

    def _source_worker(self, source_name: str):
        """Worker thread for a data source"""
        source = self.sources[source_name]

        while self.running:
            # Fetch data
            data = self.fetch_data(source_name)

            if data is not None:
                # Process data
                processed = self.process_data(data, {'source': source_name})

                # Here you would typically store the processed data
                # For now, just log it
                pass

            # Sleep until next fetch
            time.sleep(source['interval'])

    def get_source_status(self) -> List[Dict]:
        """Get status of all data sources"""
        status = []

        for name, source in self.sources.items():
            status.append({
                'name': name,
                'interval': source['interval'],
                'last_fetch': source['last_fetch'].isoformat() if source['last_fetch'] else None,
                'error_count': source['error_count']
            })

        return status


# Example data sources
def fetch_market_data() -> Dict:
    """Example: Fetch market data"""
    # This would call an actual market data API
    return {
        'timestamp': datetime.now().isoformat(),
        'symbols': {
            'NQ': {'price': 16545.0, 'volume': 125000},
            'ES': {'price': 4800.5, 'volume': 85000}
        }
    }

def fetch_news_data() -> List[Dict]:
    """Example: Fetch news data"""
    # This would call a news API
    return []

def fetch_social_sentiment() -> Dict:
    """Example: Fetch social media sentiment"""
    # This would call Twitter/Reddit APIs
    return {'sentiment_score': 0.65}


# Example processors
def normalize_data(data: any, metadata: Dict) -> any:
    """Example: Normalize data"""
    # Add metadata
    if isinstance(data, dict):
        data['_metadata'] = metadata
        data['_processed_at'] = datetime.now().isoformat()

    return data

def validate_data(data: any, metadata: Dict) -> any:
    """Example: Validate data"""
    # Check for required fields
    if isinstance(data, dict):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()

    return data


if __name__ == '__main__':
    # Test the system
    pipeline = DataPipeline()

    # Register sources
    pipeline.register_source('market_data', fetch_market_data, interval_seconds=5)
    pipeline.register_source('news', fetch_news_data, interval_seconds=60)
    pipeline.register_source('sentiment', fetch_social_sentiment, interval_seconds=30)

    # Register processors
    pipeline.register_processor(normalize_data)
    pipeline.register_processor(validate_data)

    print("Data Pipeline ready!")

    # Start pipeline
    print("\nStarting pipeline...")
    pipeline.start()

    # Let it run for a bit
    print("Pipeline running (press Ctrl+C to stop)...")
    try:
        while True:
            time.sleep(5)

            # Show status
            status = pipeline.get_source_status()
            print(f"\nSource status:")
            for s in status:
                print(f"  {s['name']}: last_fetch={s['last_fetch']}, errors={s['error_count']}")

    except KeyboardInterrupt:
        print("\nStopping pipeline...")
        pipeline.stop()
