import os
import logging
import urllib.parse
from apify_client import ApifyClient

logger = logging.getLogger("aura.tools.apify")

def get_apify_client() -> ApifyClient:
    """Return an initialized ApifyClient."""
    token = os.environ.get("APIFY_API_TOKEN", "")
    if not token:
        raise ValueError("APIFY_API_TOKEN is not set in environment variables.")
    return ApifyClient(token)

def _extract_apify_items(dataset_id: str, client: ApifyClient, max_items: int = 5) -> list:
    """Helper to fetch items from a dataset."""
    dataset_client = client.dataset(dataset_id)
    res = dataset_client.list_items(limit=max_items)
    return res.items

def scrape_social_apify(url: str, platform: str = "") -> dict:
    """Scrape social media and e-commerce URLs using Apify Actors.
    
    Args:
        url: The URL to scrape.
        platform: 'facebook', 'twitter', 'instagram', 'threads', 'shopee' (Optional, auto-detected if empty)
    """
    logger.info(f"[APIFY] Starting scrape for URL: {url} | Hint: {platform}")
    
    try:
        client = get_apify_client()
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # Auto-detect platform if not provided
    domain = urllib.parse.urlparse(url).netloc.lower()
    if not platform:
        if "facebook.com" in domain or "fb.watch" in domain:
            platform = "facebook"
        elif "twitter.com" in domain or "x.com" in domain:
            platform = "twitter"
        elif "instagram.com" in domain:
            platform = "instagram"
        elif "threads.net" in domain:
            platform = "threads"
        elif "shopee.com" in domain or "shopee." in domain:
            platform = "shopee"
        else:
            return {"status": "error", "error": f"Unsupported or unrecognized domain for Apify: {domain}"}

    actor_id = ""
    run_input = {}

    if platform == "facebook":
        actor_id = "apify/facebook-posts-scraper"
        run_input = {
            "startUrls": [{"url": url}],
            "resultsLimit": 1
        }
    elif platform == "twitter":
        actor_id = "apify/twitter-scraper"
        run_input = {
            "startUrls": [{"url": url}],
            "tweetsDesired": 1
        }
    elif platform == "threads":
        actor_id = "apify/threads-scraper"
        run_input = {
            "startUrls": [{"url": url}],
            "maxPosts": 1
        }
    elif platform == "instagram":
        actor_id = "apify/instagram-scraper"
        run_input = {
            "directUrls": [url],
            "resultsLimit": 1
        }
    elif platform == "shopee":
        # Shopee scraper by dtrungnguyen
        actor_id = "dtrungnguyen/shopee-scraper"
        run_input = {
            "startUrls": [{"url": url}],
            "maxItems": 1
        }
    else:
        return {"status": "error", "error": f"Platform '{platform}' not mapped to an Apify Actor."}

    logger.info(f"[APIFY] Using actor {actor_id}")
    
    try:
        # Call the actor and wait for it to finish (this blocks the thread)
        run = client.actor(actor_id).call(run_input=run_input, timeout_secs=90)
        
        if run is None:
            return {"status": "error", "error": "Actor call returned None. Timeout?"}
        
        status = run.get("status")
        if status != "SUCCEEDED":
            return {"status": "error", "error": f"Actor run failed with status: {status}"}

        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return {"status": "error", "error": "No dataset ID returned by actor."}

        items = _extract_apify_items(dataset_id, client)
        
        if not items:
            return {"status": "success", "content": "No items returned by scraper.", "url": url}

        # Build a generic response summarizing the first item
        item = items[0]
        
        # Extract common fields based on known schemas
        title = item.get("title") or item.get("text") or item.get("caption") or item.get("name") or f"{platform.title()} Post"
        
        # Some scrapers return text in different fields
        content = item.get("text") or item.get("fullText") or item.get("description") or item.get("caption") or str(item)
        
        images = []
        if item.get("images") and isinstance(item.get("images"), list):
            images.extend(item.get("images"))
        elif item.get("displayUrl"):
            images.append(item.get("displayUrl"))
        elif item.get("imageUrl"):
            images.append(item.get("imageUrl"))

        return {
            "status": "success",
            "tier": "apify",
            "title": title,
            "content": content,
            "images": images[:3], # Limit images
            "url": url,
            "platform": platform,
            "raw_data": items # keep raw data just in case
        }
        
    except Exception as e:
        logger.error(f"[APIFY ERROR] {str(e)}", exc_info=True)
        return {"status": "error", "error": f"Apify exception: {str(e)}"}
