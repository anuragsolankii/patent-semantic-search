import os
from typing import List
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env
load_dotenv()

class SummarizationService:
    def __init__(self):
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        
        print("GROQ_API_KEY loaded.")  # Optional debug log
        self.client = Groq(api_key=groq_api_key)

    def summarize_descriptions(self, descriptions: List[str]) -> str:
        """Summarize multiple patent descriptions using Groq LLaMA-3 model."""
        if not descriptions:
            return "No descriptions available for summarization."

        combined_text = "\n\n".join([desc for desc in descriptions if desc])
        if not combined_text.strip():
            return "No valid descriptions found for summarization."

        try:
            return self._summarize_with_groq(combined_text)
        except Exception as e:
            print(f"Groq API error: {e}")
            return self._simple_summarization(combined_text)

    def _summarize_with_groq(self, text: str) -> str:
        """Use Groq API (LLaMA-3) for summarization."""
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        prompt = f"""
        Please provide a comprehensive summary of the following patent descriptions. 
        Focus on the main innovations, technical solutions, and key features described.
        Make the summary technical yet accessible, highlighting the practical applications and benefits:

        {text}

        Summary:
        """

        response = self.client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are a technical expert specializing in patent analysis and summarization."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=512,
            top_p=1,
            stream=False,
        )

        return response.choices[0].message.content.strip()

    def _simple_summarization(self, text: str) -> str:
        """Simple fallback summarization (extractive)."""
        try:
            sentences = text.split('. ')
            summary_sentences = []
            current_length = 0
            max_length = 500

            for sentence in sentences:
                if current_length + len(sentence) < max_length:
                    summary_sentences.append(sentence.strip())
                    current_length += len(sentence)
                else:
                    break

            summary = '. '.join(summary_sentences)
            if not summary.endswith('.'):
                summary += '.'

            fallback_note = "\n\n[Note: This summary was generated using a simple extraction method. For better summaries, ensure Groq is available.]"
            return summary + fallback_note

        except Exception as e:
            return f"Error generating fallback summary: {str(e)}"
