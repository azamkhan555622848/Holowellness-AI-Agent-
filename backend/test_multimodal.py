import requests
import base64
import json
import os

# Configuration
API_URL = "http://localhost:5000/api/chat"  # Point to main backend
# Or direct to microservice if testing that: "http://localhost:9000/v1/rag/query"

IMAGE_PATH = "src/lovable-uploads/320d61e5-9a63-4856-887a-7ac4bd694b9b.png"

# Sample metrics provided by user
METRICS = {
  "metrics_by_view": {
    "front": {
      "cervical_lateral_shift": {
        "value": 3.1,
        "unit": "%",
        "class": 1,
        "label": "Cervical lateral shift",
        "thresholds": {
          "ok_max": 1.25,
          "partial_max": 3.75
        },
        "factors": [
          "shoulder_width"
        ],
        "proxy": True
      },
      "pelvic_obliquity": {
        "value": 2.6,
        "unit": "deg",
        "class": 0,
        "label": "Pelvic obliquity (frontal)",
        "thresholds": {
          "ok_max": 4.5,
          "partial_max": 8
        },
        "factors": [],
        "proxy": False
      },
      "knee_valgus_left": {
        "value": 2.1,
        "unit": "deg",
        "class": 1,
        "label": "Knee varus/valgus deviation (HKA) L",
        "thresholds": {
          "ok_dev": 2,
          "partial_dev": 5
        },
        "factors": [
          "sex"
        ],
        "proxy": True
      },
      "knee_valgus_right": {
        "value": 2.3,
        "unit": "deg",
        "class": 1,
        "label": "Knee varus/valgus deviation (HKA) R",
        "thresholds": {
          "ok_dev": 2,
          "partial_dev": 5
        },
        "factors": [
          "sex"
        ],
        "proxy": True
      },
      "elbow_carry_angle_left": {
        "value": 12.8,
        "unit": "deg",
        "class": 0,
        "label": "Elbow carrying angle L",
        "thresholds": {
          "male": "11–14",
          "female": "13–16",
          "current": "11–14"
        },
        "factors": [
          "sex"
        ],
        "proxy": False
      },
      "elbow_carry_angle_right": {
        "value": 22.8,
        "unit": "deg",
        "class": 2,
        "label": "Elbow carrying angle R",
        "thresholds": {
          "male": "11–14",
          "female": "13–16",
          "current": "11–14"
        },
        "factors": [
          "sex"
        ],
        "proxy": False
      },
      "shoulder_line_tilt_front": {
        "value": 3.2,
        "unit": "deg",
        "class": 0,
        "label": "Shoulder line tilt",
        "thresholds": {
          "ok_max": 5,
          "partial_max": 10
        },
        "factors": [],
        "proxy": False
      }
    },
    "left": {
      "neck_forward_head": {
        "value": 15.9,
        "unit": "deg",
        "class": 1,
        "label": "Forward head posture",
        "thresholds": {
          "ok_max": 10,
          "partial_max": 18
        },
        "factors": [
          "age"
        ],
        "proxy": True
      },
      "thoracic_hypokyphosis": {
        "value": 34.5,
        "unit": "deg",
        "class": 2,
        "label": "Thoracic hypokyphosis proxy",
        "thresholds": {
          "ok_range": "20–25",
          "partial_range": "15–20",
          "severe_max": 15
        },
        "factors": [],
        "proxy": True
      }
    }
  }
}

def encode_image(image_path):
    """Encodes a local image file to base64 string."""
    if not os.path.exists(image_path):
        print(f"Warning: Image path {image_path} not found. Sending request without image.")
        return None
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_rag_query():
    print(f"Testing RAG query against {API_URL}...")
    
    # Prepare payload
    payload = {
        "query": "Based on these metrics and the image, how is my squat posture?",
        "metrics": METRICS,
        "top_k": 5
    }
    
    # Add image if available
    # Try to find an image in the workspace if the hardcoded one fails
    image_path = IMAGE_PATH
    if not os.path.exists(image_path):
         # Fallback to try and find any png in src/
         for root, dirs, files in os.walk("src"):
             for f in files:
                 if f.endswith(".png"):
                     image_path = os.path.join(root, f)
                     break
    
    img_b64 = encode_image(image_path)
    if img_b64:
        print(f"Encoding image from: {image_path}")
        payload["image_base64"] = img_b64
    
    # Send request
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            print("\nSuccess!")
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\nException: {e}")

if __name__ == "__main__":
    test_rag_query()

