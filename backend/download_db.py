#!/usr/bin/env python3
"""
Download NBA database from S3 during Render build process
"""

import boto3
import os
import sys

def download_database():
    """Download database from S3 during build"""
    try:
        print("🔄 Starting database download from S3...")
        
        # Get environment variables
        bucket_name = os.getenv('S3_BUCKET_NAME', 'nba-duckdb-bucket')
        db_key = os.getenv('S3_DB_KEY', 'nba_clean.db')
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        print(f"📦 S3 Bucket: {bucket_name}")
        print(f"🗄️ Database Key: {db_key}")
        print(f"🌍 AWS Region: {aws_region}")
        
        # Create S3 client
        s3 = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Download database
        print(f"⬇️ Downloading {db_key} from {bucket_name}...")
        s3.download_file(bucket_name, db_key, 'nba_clean.db')
        
        # Verify file exists and get size
        if os.path.exists('nba_clean.db'):
            file_size = os.path.getsize('nba_clean.db')
            print(f"✅ Database downloaded successfully!")
            print(f"📊 File size: {file_size / (1024*1024):.2f} MB")
        else:
            print("❌ Database file not found after download")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error downloading database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    download_database()
