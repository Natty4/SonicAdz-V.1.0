import time
from django.utils.text import slugify
from urllib.parse import urlparse
from cloudinary import uploader
from rest_framework import serializers

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
    
    
def get_unique_public_id(headline):
    """
    Creates a unique public ID by slugifying the headline
    and appending a timestamp.
    """
    base_slug = slugify(headline)
    timestamp = int(time.time())
    return f"ad_media/{base_slug}-{timestamp}"

def upload_to_cloudinary(file_object, public_id):
    """
    Uploads a file object (like a DRF UploadedFile) to Cloudinary.
    Returns the secure URL of the uploaded media.
    """
    try:
        # The upload method can take a file-like object directly
        result = uploader.upload(
            file_object, 
            folder='sonicadz_campaigns',
            public_id=public_id,
            resource_type="auto")
        return result['secure_url']
    except Exception as e:
       
        raise serializers.ValidationError(
            {'img_url': f"Error uploading file to Cloudinary: {e}"}
        )
        