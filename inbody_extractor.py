import google.generativeai as genai
import json
import os
import base64
import re
from dotenv import load_dotenv

# =========================
# Load Environment
# =========================
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found")

genai.configure(api_key=GEMINI_API_KEY)


class InBodyExtractor:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def extract_from_bytes(self, image_bytes: bytes, mime_type: str):

        try:
            img_data = base64.b64encode(image_bytes).decode()

            prompt = """
            Extract InBody data in JSON only:

            {
              "age": number,
              "gender": "Male or Female",
              "weight": number,
              "height": number,
              "smm": number,
              "body_fat_mass": number,
              "ffm": number,
              "muscle_percentage": number,
              "fat_percentage": number,
              "water_percentage": number,
              "bmr": number
            }

            Rules:
            - No explanation
            - Missing = -1
            """

            image_part = {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": img_data
                }
            }

            response = self.model.generate_content([prompt, image_part])
            text = response.text.strip()

            match = re.search(r'\{.*\}', text, re.DOTALL)
            if not match:
                raise ValueError("❌ JSON not found")

            data = json.loads(match.group())

            return self._post_process(data)

        except json.JSONDecodeError:
            return self._extract_numbers(text)

        except Exception as e:
            return {"error": str(e)}

    # =========================
    def _post_process(self, data: dict):

        weight = data.get("weight", -1)
        fat_mass = data.get("body_fat_mass", -1)
        smm = data.get("smm", -1)
        ffm = data.get("ffm", -1)

        # FFM
        if ffm == -1 and weight > 0 and fat_mass > 0:
            data["ffm"] = weight - fat_mass

        # Fat %
        if data.get("fat_percentage", -1) == -1 and fat_mass > 0 and weight > 0:
            data["fat_percentage"] = (fat_mass / weight) * 100

        # Muscle %
        if data.get("muscle_percentage", -1) == -1:
            if smm > 0 and weight > 0:
                data["muscle_percentage"] = (smm / weight) * 100

        # Water %
        if data.get("water_percentage", -1) == -1 and ffm > 0 and weight > 0:
            data["water_percentage"] = (ffm * 0.73 / weight) * 100

        # BMR
        if data.get("bmr", -1) == -1:
            age = data.get("age", -1)
            height = data.get("height", -1)
            gender = str(data.get("gender", "")).lower()

            if weight > 0 and height > 0 and age > 0:
                if "male" in gender:
                    data["bmr"] = 10 * weight + 6.25 * height - 5 * age + 5
                elif "female" in gender:
                    data["bmr"] = 10 * weight + 6.25 * height - 5 * age - 161

        # rounding
        for k, v in data.items():
            if isinstance(v, float):
                data[k] = round(v, 2)

        return data

    # =========================
    def _extract_numbers(self, text: str):

        numbers = re.findall(r'\d+\.?\d*', text)

        return {
            "age": int(numbers[0]) if len(numbers) > 0 else -1,
            "gender": "Male",
            "weight": float(numbers[1]) if len(numbers) > 1 else -1,
            "height": float(numbers[2]) if len(numbers) > 2 else -1,
            "smm": float(numbers[3]) if len(numbers) > 3 else -1,
            "body_fat_mass": float(numbers[4]) if len(numbers) > 4 else -1,
            "ffm": float(numbers[5]) if len(numbers) > 5 else -1,
            "muscle_percentage": float(numbers[6]) if len(numbers) > 6 else -1,
            "fat_percentage": float(numbers[7]) if len(numbers) > 7 else -1,
            "water_percentage": float(numbers[8]) if len(numbers) > 8 else -1,
            "bmr": int(numbers[9]) if len(numbers) > 9 else -1,
        }