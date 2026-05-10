import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
for model_name in ["models/gemini-2.0-flash", "models/gemini-1.5-flash"]:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, world!")
        print(f"{model_name}: Success")
    except Exception as e:
        print(f"{model_name}: Failed with {e}")
