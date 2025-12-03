import logging
import os
import urllib.parse
from typing import Optional, Tuple

import aioboto3
import dotenv
from botocore.exceptions import ClientError

dotenv.load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
required_env = [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME]
if not all(required_env):
    raise EnvironmentError("Missing one or more required AWS environment variables.")

logger = logging.getLogger(__name__)

CONTENT_TYPE_MAP = {
    (".mp3", ".mpeg"): "audio/mpeg",
    (".wav",): "audio/wav",
    (".txt",): "text/plain",
    (".html",): "text/html; charset=utf-8",
    (".mp4",): "video/mp4",
    (".mov",): "video/quicktime",
    (".pdf",): "application/pdf",
    (".docx",): "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    (".doc",): "application/msword",
    (".xls",): "application/vnd.ms-excel",
}


def _get_content_type(file_name: str) -> str:
    """Determine content type based on file extension."""
    lower_name = file_name.lower()
    for extensions, content_type in CONTENT_TYPE_MAP.items():
        if lower_name.endswith(extensions):
            return content_type
    return "application/octet-stream"


class BotoService:
    """Async S3 service using aioboto3."""

    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        self.bucket_name = S3_BUCKET_NAME

    async def upload_user_file(
        self,
        file_name: str,
        user_id: str,
        feature_name: str,
        project_id: str,
        object_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Upload a file to S3 bucket in a user-specific folder structure."""
        if object_name is None:
            object_name = os.path.basename(file_name)

        object_key = f"user_{user_id}/{feature_name}/{project_id}/{object_name}"
        content_type = _get_content_type(file_name)

        try:
            async with self.session.client("s3") as s3:
                await s3.upload_file(
                    file_name,
                    self.bucket_name,
                    object_key,
                    ExtraArgs={
                        "ContentType": content_type,
                        "ContentDisposition": "inline",
                    },
                )

            public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"
            return True, public_url.replace("\\", "/")

        except ClientError as e:
            logger.error(f"Upload failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            return False, None

    async def download_user_file(
        self, public_url: str, download_path: str, bucket: Optional[str] = None
    ) -> bool:
        """Download a file from S3 bucket using its public URL."""
        bucket = bucket or self.bucket_name

        try:
            parsed = urllib.parse.urlparse(public_url)
            if not parsed.netloc or bucket not in parsed.netloc:
                logger.error(f"Malformed or non-matching S3 URL: {public_url}")
                return False

            object_key = parsed.path.lstrip("/")
            if not object_key:
                logger.error(f"Could not extract object key from URL: {public_url}")
                return False
            object_key = urllib.parse.unquote(object_key)

            os.makedirs(os.path.dirname(download_path), exist_ok=True)

            logger.info(f"Downloading file from bucket: {bucket}")
            logger.info(f"Object key: {object_key}")
            logger.info(f"Download path: {download_path}")

            async with self.session.client("s3") as s3:
                await s3.download_file(bucket, object_key, download_path)

            if os.path.exists(download_path):
                file_size = os.path.getsize(download_path)
                logger.info(f"Download successful. File size: {file_size} bytes")
                return True

            logger.error("File was not created")
            return False

        except ClientError as e:
            logger.error(f"Download failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return False

    async def delete_user_file(
        self, public_url: str, bucket: Optional[str] = None
    ) -> bool:
        """Delete a file from S3 bucket using its public URL."""
        bucket = bucket or self.bucket_name

        try:
            object_key = public_url.split(f"{bucket}.s3.amazonaws.com/")[1]

            async with self.session.client("s3") as s3:
                await s3.delete_object(Bucket=bucket, Key=object_key)

            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
