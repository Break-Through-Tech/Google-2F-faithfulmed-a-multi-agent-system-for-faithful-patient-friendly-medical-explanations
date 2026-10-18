import os
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

from google import genai
from google.genai import types

def run_simplifier(atoms: str, retrieved_context: str) -> str:
    """
    Simplifier Agent: Drafts a patient-friendly medical explanation.
    
    Inputs:
    - atoms: Short, source-linked patient facts from the Extractor.
    - retrieved_context: MedlinePlus text and URL used as general background.
    
    Output:
    - draft: First patient-friendly explanation.
    """
    # Initialize Gemini client
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    # system instructions to enforce Simplifier's specific rules
    system_instruction = (
        "You are a medical simplification agent. Your job is to write a patient-friendly "
        "explanation using only the provided facts.\n\n"
        "RULES:\n"
        "1. Explain medical terms plainly using a middle-school reading level.\n"
        "2. Strictly separate general medical information (from the MedlinePlus context) "
        "from specific patient facts (from the extracted atoms). Do not state that general "
        "symptoms or treatments apply to this specific patient unless the atoms confirm it.\n"
        "3. Keep the output concise and structured."
    )
    
    # create prompt using inputs agreed upon
    prompt = f"""
    Patient Facts (Atoms):
    {atoms}
    
    General Background (MedlinePlus Context):
    {retrieved_context}
    
    Draft the explanation:
    """
    
    # Gemini call
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2, # low for factual drafting
        ),
    )
    
    return response.text

# Test block for local verification
if __name__ == "__main__":
    sample_atoms = "- Patient has elevated blood pressure (145/90).\n- Prescribed Lisinopril 10mg."
    sample_context = (
        "MedlinePlus Glossary entry: Lisinopril is in a class of medications called "
        "angiotensin-converting enzyme (ACE) inhibitors. It works by decreasing certain "
        "chemicals that tighten the blood vessels, so blood flows more smoothly and the "
        "heart can pump blood more efficiently. "
        "(Source: https://medlineplus.gov/)"
    )
    
    print("Drafting explanation...\n")
    draft = run_simplifier(sample_atoms, sample_context)
    print(draft)