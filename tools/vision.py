"""Claude Vision — proof-of-delivery photo verification.

Uses Claude's multimodal vision capability to analyse delivery photos and
verify them against expected customer addresses. This replaces the previous
string-comparison simulation with real AI-powered image analysis.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_TOKENS

# Supported image formats for Claude Vision
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _encode_image(image_path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, media_type)."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported image format '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return data, media_type


def analyse_delivery_photo(
    image_path: str,
    expected_address: str,
    delivery_id: str = "",
    driver_name: str = "",
) -> dict[str, Any]:
    """Analyse a proof-of-delivery photo using Claude Vision.

    Claude will examine the image for:
    - Any visible address, house number, street name, or postcode
    - Whether the location matches the expected delivery address
    - Package/food delivery evidence (parcels, bags, doorstep placement)
    - Any issues (wrong location, unclear photo, missing package)

    Returns a structured result dict with the analysis.
    """
    image_data, media_type = _encode_image(image_path)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are verifying a proof-of-delivery photo for Empress Family Feast.

EXPECTED DELIVERY ADDRESS: {expected_address}
{f"DELIVERY ID: {delivery_id}" if delivery_id else ""}
{f"DRIVER: {driver_name}" if driver_name else ""}

Analyse this photo carefully and provide:

1. **Address Evidence**: Any house number, street name, postcode, or identifiable location markers visible in the photo.
2. **Address Match**: Does the visible address evidence match the expected address? Answer: MATCH, MISMATCH, or INCONCLUSIVE.
3. **Delivery Evidence**: Is there visible evidence of a delivery (package, food bag, item left at door, handoff to person)?
4. **Photo Quality**: Is the photo clear enough to verify the delivery? Answer: GOOD, ACCEPTABLE, or POOR.
5. **Issues**: Any concerns (wrong location, blurry, no package visible, suspicious).

Respond ONLY with valid JSON in this exact format:
{{
    "address_found": "the address or location details visible in the photo, or null if none",
    "address_match": "MATCH or MISMATCH or INCONCLUSIVE",
    "confidence": 0.0 to 1.0,
    "delivery_evidence": true or false,
    "photo_quality": "GOOD or ACCEPTABLE or POOR",
    "issues": ["list of any issues found, empty if none"],
    "summary": "One sentence summary of the verification result"
}}"""

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Extract JSON from the response (handle markdown code blocks)
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        json_lines = []
        inside = False
        for line in lines:
            if line.startswith("```") and not inside:
                inside = True
                continue
            elif line.startswith("```") and inside:
                break
            elif inside:
                json_lines.append(line)
        raw_text = "\n".join(json_lines)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        result = {
            "address_found": None,
            "address_match": "INCONCLUSIVE",
            "confidence": 0.0,
            "delivery_evidence": False,
            "photo_quality": "POOR",
            "issues": ["Could not parse vision analysis response"],
            "summary": f"Raw response: {raw_text[:500]}",
        }

    result["delivery_id"] = delivery_id
    result["expected_address"] = expected_address
    result["photo_path"] = image_path
    result["driver"] = driver_name

    return result


def verify_delivery_photo_tool(**kwargs: Any) -> str:
    """Tool wrapper for analyse_delivery_photo — used by ERIC via tool registry."""
    image_path = kwargs["image_path"]
    delivery_id = kwargs["delivery_id"]

    # We need the database to look up the expected address
    from db.database import get_db

    db = get_db()
    delivery = db.get_delivery(delivery_id)
    if delivery is None:
        return json.dumps({"error": f"Delivery '{delivery_id}' not found."})

    expected_address = delivery["address"]
    driver_name = delivery["driver"]

    try:
        result = analyse_delivery_photo(
            image_path=image_path,
            expected_address=expected_address,
            delivery_id=delivery_id,
            driver_name=driver_name,
        )
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Persist the verification result
    import datetime

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.add_photo_verification(
        delivery_id=delivery_id,
        photo_path=image_path,
        expected_address=expected_address,
        vision_result=json.dumps(result),
        address_found=result.get("address_found"),
        match_result=result["address_match"],
        confidence=result.get("confidence"),
        details=result.get("summary"),
        verified_at=now,
    )

    # Update delivery status based on result
    match = result["address_match"]
    if match == "MATCH" and result.get("delivery_evidence"):
        db.update_delivery_status(delivery_id, "delivered", now)
        db.update_delivery_photo(delivery_id, verified=True, photo_path=image_path,
                                  vision_analysis=result.get("summary"))
    elif match == "MISMATCH":
        db.update_delivery_status(delivery_id, "photo_mismatch", now)
        db.update_delivery_photo(delivery_id, verified=False, photo_path=image_path,
                                  vision_analysis=result.get("summary"))
    else:
        db.update_delivery_photo(delivery_id, verified=False, photo_path=image_path,
                                  vision_analysis=result.get("summary"))

    return json.dumps(result, indent=2)


def analyse_photo_standalone_tool(**kwargs: Any) -> str:
    """Analyse any photo with Claude Vision without needing a delivery ID.

    Useful for general photo inspection or when the delivery ID isn't known yet.
    """
    image_path = kwargs["image_path"]
    description = kwargs.get("description", "Describe what you see in this photo in detail.")

    try:
        image_data, media_type = _encode_image(image_path)
    except (FileNotFoundError, ValueError) as e:
        return json.dumps({"error": str(e)})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": description,
                    },
                ],
            }
        ],
    )

    return json.dumps({
        "photo_path": image_path,
        "analysis": response.content[0].text,
    }, indent=2)
